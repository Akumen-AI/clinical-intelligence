import io
import os
from typing import Optional
from PIL import Image, ImageFile
import pypdf

# Enable PIL to raise exceptions on truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = False

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff"}

ALLOWED_MIME_TYPES = {
    "pdf": {"application/pdf", "application/x-pdf"},
    "png": {"image/png"},
    "jpg": {"image/jpeg", "image/pjpeg"},
    "jpeg": {"image/jpeg", "image/pjpeg"},
    "tiff": {"image/tiff", "image/x-tiff"}
}

MAX_FILE_SIZE_MB = 20.0
MAX_FILE_SIZE_BYTES = int(MAX_FILE_SIZE_MB * 1024 * 1024)

# Standardized Error Messages
ERR_UNSUPPORTED_TYPE = "This file type is not supported. Upload PDF, JPG, PNG or TIFF."
ERR_CORRUPTED_PDF = "The uploaded PDF is corrupted or unreadable."
ERR_CORRUPTED_IMAGE = "The uploaded image could not be processed."
ERR_EMPTY_FILE = "The uploaded file is empty."
ERR_LARGE_FILE = "File exceeds maximum upload size."

class FileValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def validate_extension(filename: str) -> str:
    """
    Validates the file extension against allowed clinical document formats.
    Returns normalized lowercase extension.
    """
    if not filename or "." not in filename:
        raise FileValidationError(ERR_UNSUPPORTED_TYPE)
    
    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(ERR_UNSUPPORTED_TYPE)
    
    return ext

def validate_mime_type(content_type: Optional[str], extension: str) -> None:
    """
    Validates MIME type header matching the extension if provided.
    """
    if not content_type:
        return
    
    clean_mime = content_type.split(";")[0].strip().lower()
    
    # Generic binary fallback often sent by browsers
    if clean_mime in {"application/octet-stream", "binary/octet-stream"}:
        return

    allowed_mimes = ALLOWED_MIME_TYPES.get(extension, set())
    if allowed_mimes and clean_mime not in allowed_mimes:
        raise FileValidationError(ERR_UNSUPPORTED_TYPE)

def validate_file_size(file_bytes: bytes, max_size_mb: float = MAX_FILE_SIZE_MB) -> None:
    """
    Validates file size is non-zero and within maximum upload size limit.
    """
    if len(file_bytes) == 0:
        raise FileValidationError(ERR_EMPTY_FILE)
    
    max_bytes = int(max_size_mb * 1024 * 1024)
    if len(file_bytes) > max_bytes:
        raise FileValidationError(ERR_LARGE_FILE)

def validate_pdf(file_bytes: bytes) -> None:
    """
    Validates PDF file integrity, readability, page count, and encryption.
    """
    try:
        pdf_stream = io.BytesIO(file_bytes)
        reader = pypdf.PdfReader(pdf_stream)
        
        if reader.is_encrypted:
            raise FileValidationError(ERR_CORRUPTED_PDF)
        
        if len(reader.pages) == 0:
            raise FileValidationError(ERR_CORRUPTED_PDF)
        
        # Verify page content readability
        _ = reader.pages[0].extract_text()
    except FileValidationError:
        raise
    except Exception:
        raise FileValidationError(ERR_CORRUPTED_PDF)

def validate_image(file_bytes: bytes, extension: str) -> None:
    """
    Validates image header, integrity, non-truncation, and TIFF readability using Pillow.
    """
    try:
        img_stream = io.BytesIO(file_bytes)
        img = Image.open(img_stream)
        
        # Verify image format and header
        img.verify()
        
        # Re-open stream because verify() alters image stream state
        img_stream.seek(0)
        img_load = Image.open(img_stream)
        
        # Load pixel data to catch truncation or bad encoding
        img_load.load()
        
        # Additional check for TIFF format frames
        if extension in {"tiff", "tif"}:
            n_frames = getattr(img_load, "n_frames", 1)
            for frame in range(n_frames):
                img_load.seek(frame)
                img_load.load()

    except FileValidationError:
        raise
    except Exception:
        raise FileValidationError(ERR_CORRUPTED_IMAGE)

def detect_corruption(file_bytes: bytes, filename: str, content_type: Optional[str] = None) -> str:
    """
    Main validation function running file size, extension, MIME type,
    and format-specific integrity/corruption checks.
    """
    # 1. File size check (empty & max size)
    validate_file_size(file_bytes)
    
    # 2. Extension check
    ext = validate_extension(filename)
    
    # 3. MIME type check
    validate_mime_type(content_type, ext)
    
    # 4. Format-specific corruption & integrity check
    if ext == "pdf":
        validate_pdf(file_bytes)
    elif ext in {"png", "jpg", "jpeg", "tiff"}:
        validate_image(file_bytes, ext)
    
    return ext
