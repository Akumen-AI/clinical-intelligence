"""
Text extraction service for document classification pipeline.

Extracts text from PDFs (embedded text) and images (via PaddleOCR).
Used by the classification step to get actual document content instead of mock text.

MEMORY SAFETY:
PaddleOCR is run in an isolated subprocess to prevent memory exhaustion
on resource-constrained machines (e.g., M1 MacBook Air with 8GB RAM).
PaddleOCR 3.7.0 loads ~5 neural network models (~2-3GB). Running them
in-process alongside Ollama causes the OS OOM-killer to terminate Python.

The subprocess loads models, extracts text, and exits — returning all
allocated memory to the OS. Uses 'spawn' start method for cross-platform
compatibility (macOS, Windows, and Linux).
"""

import os
import gc
import queue
import multiprocessing
import fitz  # PyMuPDF


# Resolve backend root directory once
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Timeout for OCR subprocess (seconds). PaddleOCR model loading can be slow
# on first run; subsequent runs use cached model files.
_OCR_SUBPROCESS_TIMEOUT = 300


def _reconstruct_spatial_layout(texts: list, boxes, scores=None) -> str:
    """
    Reconstruct a 2D text layout from OCR text fragments and their bounding boxes.

    PaddleOCR returns a flat list of text fragments (rec_texts) with bounding
    boxes (rec_boxes) as [x_min, y_min, x_max, y_max]. Without reconstruction,
    joining fragments with newlines destroys tabular structure — causing lab
    report columns (test name, value, unit, reference range) to be read as
    separate unrelated lines.

    This function:
    1. Groups fragments into rows by y-coordinate proximity (same visual line)
    2. Sorts each row left-to-right by x-coordinate
    3. Uses tab separation for significant horizontal gaps (column boundaries)
       and space separation for adjacent text within the same column

    Args:
        texts: List of recognized text strings from PaddleOCR.
        boxes: Array/list of bounding boxes, each as [x_min, y_min, x_max, y_max].
        scores: Optional list of confidence scores. Fragments with very low
                confidence (< 0.3) are excluded to reduce noise.

    Returns:
        Spatially-reconstructed text string with rows separated by newlines
        and columns separated by tabs.
    """
    if not texts or boxes is None or len(boxes) == 0:
        # Fallback: no spatial data available
        return "\n".join(texts).strip() if texts else ""

    # Convert boxes to plain list of lists (handles numpy arrays)
    try:
        box_list = []
        for b in boxes:
            if hasattr(b, 'tolist'):
                box_list.append(b.tolist())
            else:
                box_list.append(list(b))
    except Exception:
        return "\n".join(texts).strip()

    # Pair each text fragment with its box and optional score
    fragments = []
    for i, (text, box) in enumerate(zip(texts, box_list)):
        if not text or not text.strip():
            continue
        # Filter out very low confidence fragments if scores available
        if scores is not None and i < len(scores):
            try:
                if float(scores[i]) < 0.3:
                    continue
            except (ValueError, TypeError):
                pass
        # box format: [x_min, y_min, x_max, y_max]
        x_min, y_min, x_max, y_max = float(box[0]), float(box[1]), float(box[2]), float(box[3])
        fragments.append({
            "text": text.strip(),
            "x_min": x_min,
            "y_min": y_min,
            "x_max": x_max,
            "y_max": y_max,
            "height": y_max - y_min,
        })

    if not fragments:
        return "\n".join(texts).strip()

    # Calculate adaptive row-grouping tolerance based on median text height
    heights = sorted(f["height"] for f in fragments if f["height"] > 0)
    if heights:
        median_height = heights[len(heights) // 2]
    else:
        median_height = 15.0  # sensible default for ~300 DPI OCR

    row_tolerance = median_height * 0.5
    col_gap_threshold = median_height * 1.5

    # Sort all fragments by y_min (top to bottom), then x_min (left to right)
    fragments.sort(key=lambda f: (f["y_min"], f["x_min"]))

    # Group fragments into rows: fragments with similar y_min belong together
    rows = []
    current_row = [fragments[0]]
    for frag in fragments[1:]:
        # Compare with the average y_min of the current row
        avg_y = sum(f["y_min"] for f in current_row) / len(current_row)
        if abs(frag["y_min"] - avg_y) <= row_tolerance:
            current_row.append(frag)
        else:
            rows.append(current_row)
            current_row = [frag]
    rows.append(current_row)

    # Build the output: sort each row left-to-right, use tab for column gaps
    output_lines = []
    for row in rows:
        row.sort(key=lambda f: f["x_min"])
        line_parts = [row[0]["text"]]
        for i in range(1, len(row)):
            gap = row[i]["x_min"] - row[i - 1]["x_max"]
            if gap > col_gap_threshold:
                line_parts.append("\t")
            else:
                line_parts.append(" ")
            line_parts.append(row[i]["text"])
        output_lines.append("".join(line_parts))

    return "\n".join(output_lines).strip()


def _paddle_ocr_worker(image_paths: list, result_queue):
    """
    Subprocess worker: initializes PaddleOCR, processes image(s), puts results in queue.

    Runs in an isolated process so all PaddleOCR model memory (~2-3GB) is fully
    reclaimed by the OS when the process exits.

    Args:
        image_paths: List of absolute paths to image files.
        result_queue: multiprocessing.Queue to send results back to the parent.
    """
    results = []
    try:
        # --- Windows Compatibility Flags ---
        # PaddlePaddle's oneDNN (MKL-DNN) executor crashes on Windows with:
        #   "ConvertPirAttribute2RuntimeAttribute not support
        #    [pir::ArrayAttribute<pir::DoubleAttribute>]"
        # Disabling oneDNN and the PIR API avoids this crash.
        # These are safe no-ops on macOS and Linux.
        # Set these explicitly rather than with setdefault(): a reloader or
        # parent process may already have supplied a conflicting value.
        # PaddlePaddle 3.x also has a separate PIR executor switch; disabling
        # only FLAGS_enable_pir_api still leaves the Windows oneDNN/PIR crash.
        os.environ["FLAGS_use_mkldnn"] = "0"
        os.environ["FLAGS_use_onednn"] = "0"
        os.environ["FLAGS_enable_pir_api"] = "0"
        os.environ["FLAGS_enable_pir_in_executor"] = "0"

        from paddleocr import PaddleOCR
        # use_angle_cls=True enables text direction detection (useful for rotated docs)
        # lang='en' for English medical documents
        # enable_mkldnn=False is CRITICAL for Windows: env vars alone don't reliably
        # prevent PaddlePaddle's C++ layer from using oneDNN, which crashes with:
        #   "ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute...]"
        # This flag is a harmless no-op on macOS/Linux.
        ocr = PaddleOCR(use_angle_cls=True, lang='en', enable_mkldnn=False)

        for image_path in image_paths:
            try:
                # In PaddleOCR 3.7.0 (PaddleX based), the API uses predict()
                result = ocr.predict(image_path)

                if not result:
                    results.append("")
                    continue

                # result is a generator or list of dict-like objects
                res_dict = next(iter(result))

                # In PaddleOCR 3.7.0 / PaddleX, the result dict contains:
                #   rec_texts: list of recognized text strings
                #   rec_boxes: bounding boxes as [x_min, y_min, x_max, y_max]
                #   rec_scores: confidence scores per fragment
                # Using rec_boxes for spatial layout reconstruction preserves
                # the tabular structure of documents like lab reports.
                if hasattr(res_dict, 'keys') and 'rec_texts' in res_dict and res_dict['rec_texts']:
                    texts = res_dict['rec_texts']
                    boxes = res_dict.get('rec_boxes', None)
                    scores = res_dict.get('rec_scores', None)

                    if boxes is not None and len(boxes) == len(texts):
                        reconstructed = _reconstruct_spatial_layout(texts, boxes, scores)
                        results.append(reconstructed)
                    else:
                        # Fallback if boxes unavailable or mismatched
                        results.append("\n".join(texts).strip())
                else:
                    results.append("")
            except Exception as e:
                print(f"[Text Extraction] PaddleOCR failed for {os.path.basename(image_path)}: {e}")
                results.append("")

        # Explicitly clean up before process exits
        del ocr
        gc.collect()

    except Exception as e:
        print(f"[Text Extraction] PaddleOCR subprocess initialization failed: {e}")
        results = [""] * len(image_paths)

    result_queue.put(results)


def _run_paddle_ocr_subprocess(image_paths: list, timeout: int = _OCR_SUBPROCESS_TIMEOUT) -> list:
    """
    Run PaddleOCR in an isolated subprocess. Returns list of extracted text strings.

    Uses 'spawn' start method for cross-platform compatibility:
    - 'spawn' is the default on Windows
    - 'spawn' works correctly on macOS (avoids fork-safety issues with CoreFoundation)
    - 'spawn' works on Linux

    The subprocess loads PaddleOCR models, processes all images, and exits.
    All model memory is returned to the OS when the process terminates.

    Args:
        image_paths: List of absolute paths to image files.
        timeout: Maximum seconds to wait for the subprocess.

    Returns:
        List of extracted text strings (one per image path).
    """
    if not image_paths:
        return []

    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()
    process = ctx.Process(target=_paddle_ocr_worker, args=(image_paths, result_queue))

    print(f"[Text Extraction] Starting OCR subprocess for {len(image_paths)} image(s)...")
    process.start()
    process.join(timeout=timeout)

    if process.is_alive():
        print(f"[Text Extraction] OCR subprocess timed out after {timeout}s. Terminating.")
        process.terminate()
        process.join(timeout=5)
        # On Unix, if terminate() (SIGTERM) didn't work, escalate to kill (SIGKILL).
        # On Windows, terminate() already performs a hard kill (TerminateProcess).
        if process.is_alive():
            process.kill()
            process.join(timeout=5)
        return [""] * len(image_paths)

    # Do not use Queue.empty() here. It is inherently racy and is especially
    # unreliable with multiprocessing queues on Windows: the child may have
    # put its result on the queue while the feeder thread has not flushed it
    # yet, causing empty() to incorrectly return True.
    try:
        results = result_queue.get(timeout=5)
        print(f"[Text Extraction] OCR subprocess completed successfully.")
        return results
    except queue.Empty:
        print("[Text Extraction] OCR subprocess returned no result.")
    except Exception as e:
        print(f"[Text Extraction] Failed to read OCR subprocess result: {e}")

    return [""] * len(image_paths)


def _extract_text_with_paddle(image_path: str) -> str:
    """
    Extract text from a single image file using PaddleOCR in a subprocess.
    Returns the concatenated text from all detected regions.
    """
    results = _run_paddle_ocr_subprocess([image_path])
    return results[0] if results else ""


def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract embedded text from all pages of a PDF using PyMuPDF.
    Falls back to OCR-based extraction if no embedded text is found.
    """
    abs_path = os.path.abspath(os.path.join(_BACKEND_DIR, filepath))
    doc = fitz.open(abs_path)
    text_parts = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_text = page.get_text("text").strip()
        if page_text:
            text_parts.append(page_text)

    doc.close()

    full_text = "\n\n".join(text_parts).strip()

    # If PDF has no embedded text (scanned PDF), try OCR via image extraction
    if not full_text:
        full_text = _ocr_pdf_pages(abs_path)

    return full_text


def extract_text_from_image(filepath: str) -> str:
    """
    Extract text from an image file using PaddleOCR (in subprocess).
    """
    abs_path = os.path.abspath(os.path.join(_BACKEND_DIR, filepath))
    return _extract_text_with_paddle(abs_path)


def _ocr_pdf_pages(abs_path: str) -> str:
    """
    For scanned PDFs with no embedded text, render all pages to temp images
    and run PaddleOCR on them in a single subprocess (loads models only once).
    """
    try:
        import tempfile

        doc = fitz.open(abs_path)
        temp_paths = []

        # Render all pages to temp images first
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Render page at 300 DPI for better OCR accuracy
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(img_bytes)
                temp_paths.append(tmp.name)

        doc.close()

        # Run OCR on all pages in a single subprocess (loads models only once)
        results = _run_paddle_ocr_subprocess(temp_paths)

        # Clean up temp files
        for tmp_path in temp_paths:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        return "\n\n".join(text for text in results if text).strip()
    except Exception as e:
        print(f"[Text Extraction] OCR of scanned PDF failed: {e}")
        return ""


def extract_text(filepath: str, filetype: str) -> str:
    """
    Main entry point: extract text from a document based on its file type.

    Args:
        filepath: Relative path to the file (from backend root), e.g. 'uploads/xxx.pdf'
        filetype: File extension, e.g. 'pdf', 'png', 'jpg'

    Returns:
        Extracted text string, or empty string if extraction fails.
    """
    filetype_lower = filetype.lower()

    if filetype_lower == "pdf":
        text = extract_text_from_pdf(filepath)
    elif filetype_lower in ("png", "jpg", "jpeg", "tiff"):
        text = extract_text_from_image(filepath)
    else:
        print(f"[Text Extraction] Unsupported file type: {filetype}")
        text = ""

    if text:
        print(f"[Text Extraction] Extracted {len(text)} characters from {os.path.basename(filepath)}")
    else:
        print(f"[Text Extraction] No text extracted from {os.path.basename(filepath)}")

    return text
