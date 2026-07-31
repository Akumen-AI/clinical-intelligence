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
        ocr = PaddleOCR(use_angle_cls=True, lang='en')

        for image_path in image_paths:
            try:
                # In PaddleOCR 3.7.0 (PaddleX based), the API uses predict()
                result = ocr.predict(image_path)

                if not result:
                    results.append("")
                    continue

                # result is a generator or list of dict-like objects
                res_dict = next(iter(result))

                # In PaddleOCR 3.7.0 / PaddleX, the key is 'rec_texts' (plural)
                if hasattr(res_dict, 'keys') and 'rec_texts' in res_dict and res_dict['rec_texts']:
                    results.append("\n".join(res_dict['rec_texts']).strip())
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
