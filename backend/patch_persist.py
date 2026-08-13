with open("app/services/layout_detection_service.py", "r") as f:
    content = f.read()

content = content.replace(
    'def persist_layout_regions(db: Session, document: Document) -> List[LayoutRegion]:\n    """Run layout detection for a processed image and persist its regions."""',
    'def persist_layout_regions(db: Session, document: Document) -> List[LayoutRegion]:\n    print(f"[Debug] persist_layout_regions called for {document.document_id}")\n    """Run layout detection for a processed image and persist its regions."""'
)
content = content.replace(
    '        detections = detect_layout(path)',
    '        print(f"[Debug] Calling detect_layout for {path}")\n        detections = detect_layout(path)\n        print(f"[Debug] detect_layout returned {len(detections)} detections")'
)

with open("app/services/layout_detection_service.py", "w") as f:
    f.write(content)
