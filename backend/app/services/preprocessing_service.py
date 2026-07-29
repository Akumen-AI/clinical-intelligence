import os
import time
import cv2
import numpy as np
import fitz  # PyMuPDF

def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Deskews an image by calculating the skew angle of the text contours.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Thresholding (Otsu's binarization after inverting colors so text is white)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # Grab the coordinates of all white pixels
    pts = np.column_stack(np.where(thresh > 0))
    if len(pts) == 0:
        return image  # Nothing to deskew

    # Swap columns to convert from (row, col) to (x, y)
    coords = pts[:, ::-1]

    # Calculate the min area rect enclosing all points
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # Adjust the angle based on OpenCV minAreaRect return conventions
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Avoid rotating if the skew angle is negligible or too large
    if abs(angle) < 0.1 or abs(angle) > 45:
        return image

    # Rotate the image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def denoise_image(image: np.ndarray) -> np.ndarray:
    """
    Denoises the image using fastNlMeansDenoising (grayscale or color).
    """
    if len(image.shape) == 2:
        # Grayscale image
        return cv2.fastNlMeansDenoising(image, None, h=10, templateWindowSize=7, searchWindowSize=21)
    elif len(image.shape) == 3:
        # Color image (BGR or BGRA)
        if image.shape[2] == 4:
            bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            denoised_bgr = cv2.fastNlMeansDenoisingColored(bgr, None, h=10, hColor=10, templateWindowSize=7, searchWindowSize=21)
            return cv2.cvtColor(denoised_bgr, cv2.COLOR_BGR2BGRA)
        else:
            return cv2.fastNlMeansDenoisingColored(image, None, h=10, hColor=10, templateWindowSize=7, searchWindowSize=21)
    return image

def correct_contrast(image: np.ndarray) -> np.ndarray:
    """
    Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to correct contrast.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    if len(image.shape) == 2:
        # Grayscale
        return clahe.apply(image)
    elif len(image.shape) == 3:
        # Color image: convert to LAB, apply CLAHE to L channel, convert back to BGR/BGRA
        if image.shape[2] == 4:
            bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            enhanced_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            return cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2BGRA)
        else:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return image

def preprocess_single_image(image: np.ndarray) -> np.ndarray:
    """
    Runs deskew, denoise, and contrast correction on a single numpy image.
    """
    # 1. Deskew
    img = deskew_image(image)
    # 2. Denoise
    img = denoise_image(img)
    # 3. Correct Contrast
    img = correct_contrast(img)
    return img

def preprocess_document_file(raw_uri: str, filetype: str) -> tuple[str, int]:
    """
    Performs image preprocessing on the file at raw_uri and saves it separately.
    Returns: (processed_relative_path, elapsed_time_ms)
    """
    # Resolve absolute paths
    # Parent directory of app/services is app, parent is backend
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    original_abspath = os.path.abspath(os.path.join(backend_dir, raw_uri))
    
    # Define processed filename and path
    basename = os.path.basename(original_abspath)
    processed_filename = f"processed_{basename}"
    # Always use forward slashes for stored relative paths (cross-platform compatibility)
    processed_relative_path = "uploads/" + processed_filename
    processed_abspath = os.path.abspath(os.path.join(backend_dir, processed_relative_path))
    
    start_time = time.perf_counter()
    
    if filetype.lower() == "pdf":
        # Load PDF pages using PyMuPDF
        doc = fitz.open(original_abspath)
        out_doc = fitz.open()
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            
            # Convert pixmap to numpy array (RGB)
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            # Convert RGB/RGBA to BGR/BGRA for opencv
            if pix.n == 4:
                img = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGRA)
            else:
                img = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
                
            # Preprocess the page image
            processed_img = preprocess_single_image(img)
            
            # Convert back to PNG bytes to insert into output PDF
            _, img_encoded = cv2.imencode(".png", processed_img)
            img_bytes = img_encoded.tobytes()
            
            h, w = processed_img.shape[:2]
            new_page = out_doc.new_page(width=w, height=h)
            new_page.insert_image(fitz.Rect(0, 0, w, h), stream=img_bytes)
            
        out_doc.save(processed_abspath)
        out_doc.close()
        doc.close()
    else:
        # Load image file
        img = cv2.imread(original_abspath, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Failed to read image file at {original_abspath}")
            
        processed_img = preprocess_single_image(img)
        cv2.imwrite(processed_abspath, processed_img)
        
    elapsed_time_ms = int((time.perf_counter() - start_time) * 1000)
    
    return processed_relative_path, elapsed_time_ms
