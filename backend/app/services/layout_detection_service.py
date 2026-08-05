"""Layout detection adapter and persistence helpers.

The detector is imported lazily because LayoutParser/Detectron2 is an optional,
heavy dependency and should not prevent the upload API from starting.
"""

import os
import tempfile
from typing import Any, Dict, List

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.document import Document
from app.models.layout_region import LayoutRegion


_LABEL_MAP = {
    0: "body",    # PubLayNet: text
    1: "header",  # PubLayNet: title
    2: "body",    # PubLayNet: list
    3: "table",
    4: "other",   # PubLayNet: figure
}


def _absolute_backend_path(relative_path: str) -> str:
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.abspath(os.path.join(backend_dir, relative_path))


def detect_layout(image_path: str) -> List[Dict[str, Any]]:
    """Detect PubLayNet regions and normalize them to the platform contract."""
    try:
        import cv2
        import layoutparser as lp
    except ImportError as exc:
        raise RuntimeError(
            "Layout detection requires layoutparser, detectron2, and their model dependencies."
        ) from exc

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Unable to read layout image: {image_path}")

    model = lp.Detectron2LayoutModel(
        "lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config",
        extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.5],
        label_map=_LABEL_MAP,
    )
    detected = model.detect(image)

    regions: List[Dict[str, Any]] = []
    for block in detected:
        coordinates = [float(value) for value in block.coordinates]
        score = float(getattr(block, "score", 0.0) or 0.0)
        region_type = str(getattr(block, "type", "other")).lower()
        if region_type not in {"header", "body", "table", "other"}:
            region_type = "body" if region_type in {"text", "title", "list"} else "other"
        regions.append({
            "type": region_type,
            "bbox": coordinates,
            "confidence": max(0.0, min(1.0, score)),
        })
    return regions


def persist_layout_regions(db: Session, document: Document) -> List[LayoutRegion]:
    """Run layout detection for a processed image and persist its regions."""
    if not document.processed_uri:
        raise ValueError(f"Document '{document.document_id}' has no processed file")

    path = _absolute_backend_path(document.processed_uri)
    temporary_path = None
    if document.filetype.lower() == "pdf":
        import fitz

        pdf = fitz.open(path)
        if not pdf.page_count:
            pdf.close()
            raise ValueError(f"PDF has no pages: {path}")
        pixmap = pdf.load_page(0).get_pixmap()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as output:
            output.write(pixmap.tobytes("png"))
            temporary_path = output.name
        pdf.close()
        path = temporary_path

    try:
        detections = detect_layout(path)
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
    db.query(LayoutRegion).filter(LayoutRegion.document_id == document.document_id).delete(
        synchronize_session=False
    )

    regions = []
    for detection in detections:
        bbox = [float(value) for value in detection["bbox"]]
        if len(bbox) != 4:
            continue
        regions.append(LayoutRegion(
            document_id=document.document_id,
            region_type=detection.get("type", "other"),
            bbox=bbox,
            confidence=max(0.0, min(1.0, float(detection.get("confidence", 0.0)))),
        ))

    db.add_all(regions)
    document.status = "layout_detected"
    db.commit()
    return regions


def _run_layout_detection_after_preprocessing(document_ids: List[str], bind: Engine) -> None:
    """Run detection in a fresh session after the preprocessing transaction."""
    # Reuse the committing session's bind. This keeps test database overrides
    # and non-default DATABASE_URL deployments on the correct database.
    detection_session = sessionmaker(autocommit=False, autoflush=False, bind=bind)
    db = detection_session()
    try:
        for document_id in document_ids:
            document = db.get(Document, document_id)
            if not document or document.status != "preprocessed":
                continue
            try:
                document.status = "detecting_layout"
                db.commit()
                persist_layout_regions(db, document)
            except Exception as exc:
                db.rollback()
                document = db.get(Document, document_id)
                if document:
                    document.rejection_reason = f"Layout detection failed: {exc}"
                    db.commit()
                print(f"[Layout Detection] Failed for {document_id}: {exc}")
    finally:
        db.close()

