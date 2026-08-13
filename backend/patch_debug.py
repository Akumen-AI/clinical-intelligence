with open("app/services/layout_detection_service.py", "r") as f:
    content = f.read()

content = content.replace(
    '            if not document or document.status != "preprocessed":\n                continue',
    '            print(f"[Debug] Document: {document}, status: {document.status if document else None}")\n            if not document or document.status != "preprocessed":\n                print("[Debug] SKIPPING LAYOUT!")\n                continue'
)
content = content.replace(
    '    detection_session = sessionmaker(autocommit=False, autoflush=False, bind=bind)\n    db = detection_session()',
    '    print(f"[Debug] document_ids: {document_ids}")\n    detection_session = sessionmaker(autocommit=False, autoflush=False, bind=bind)\n    db = detection_session()'
)

with open("app/services/layout_detection_service.py", "w") as f:
    f.write(content)
