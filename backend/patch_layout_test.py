import re
with open("tests/test_layout_detection.py", "r") as f:
    content = f.read()

replacement = """
        mocker.patch(
            "app.services.layout_detection_service.detect_layout",
            side_effect=lambda image_path: (
                pipeline_events.append("layout"),
                [
                    {"type": "header", "bbox": [0, 0, 240, 45], "confidence": 0.97},
                    {"type": "body", "bbox": [0, 60, 240, 160], "confidence": 0.91},
                ],
            )[1],
        )
        mocker.patch(
            "app.services.text_extraction_service.extract_text",
            side_effect=lambda *args, **kwargs: (pipeline_events.append("ocr"), "sample clinical text")[1],
        )
"""
new_replacement = """
        def _mock_layout(*args, **kwargs):
            import traceback; print("LAYOUT CALLED FROM:"); traceback.print_stack()
            pipeline_events.append("layout")
            return [
                {"type": "header", "bbox": [0, 0, 240, 45], "confidence": 0.97},
                {"type": "body", "bbox": [0, 60, 240, 160], "confidence": 0.91},
            ]
        def _mock_ocr(*args, **kwargs):
            import traceback; print("OCR CALLED FROM:"); traceback.print_stack()
            pipeline_events.append("ocr")
            return "sample clinical text"

        mocker.patch("app.services.layout_detection_service.detect_layout", side_effect=_mock_layout)
        mocker.patch("app.services.text_extraction_service.extract_text", side_effect=_mock_ocr)
"""
content = content.replace(replacement.strip(), new_replacement.strip())
with open("tests/test_layout_detection.py", "w") as f:
    f.write(content)
