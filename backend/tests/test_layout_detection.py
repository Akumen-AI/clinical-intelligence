import io
import importlib.util
import os
import shutil
import time

import pytest
from PIL import Image, ImageDraw


def _sample_image_bytes(label: str) -> bytes:
    image = Image.new("RGB", (240, 160), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 230, 45), outline="black")
    draw.text((20, 20), label, fill="black")
    draw.rectangle((10, 60, 230, 145), outline="black")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _wait_for_status(client, document_id: str, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/v1/documents/{document_id}/status")
        if response.status_code == 200 and response.json().get("status") in ["classified", "extracted"]:
            return
        time.sleep(0.05)
    raise AssertionError("document processing did not complete")


def _wait_for_layout(client, document_id: str, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/v1/documents/{document_id}/layout")
        if response.status_code == 200 and response.json():
            return response.json()
        time.sleep(0.05)
    raise AssertionError("layout detection did not persist regions")


def test_three_document_images_persist_and_retrieve_layout_regions(client, mocker):
    pipeline_events = []
    mocker.patch(
        "app.services.preprocessing_service.preprocess_document_file",
        side_effect=lambda raw_uri, filetype: (raw_uri.replace("uploads/", "uploads/processed_"), 1),
    )
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
    mocker.patch(
        "app.services.text_extraction_service.extract_text_with_confidence",
        side_effect=lambda *args, **kwargs: (pipeline_events.append("ocr"), ("sample clinical text", [0.95]))[1],
    )

    classifier = mocker.MagicMock()
    classifier.classify.return_value.document_type = "Lab Report"
    classifier.classify.return_value.confidence = 0.95
    mocker.patch("app.services.classification.factory.get_document_classifier", return_value=classifier)
    from app.services.extraction.rule_based_extractor import RuleBasedFieldExtractor
    mocker.patch("app.services.extraction.factory.get_field_extractor", return_value=RuleBasedFieldExtractor())

    for label in ("prescription", "lab report", "discharge summary"):
        response = client.post(
            "/api/v1/documents/upload",
            files=[("files", (f"{label.replace(' ', '_')}.png", io.BytesIO(_sample_image_bytes(label)), "image/png"))],
        )
        assert response.status_code == 201
        document_id = response.json()["accepted"][0]["document_id"]
        _wait_for_status(client, document_id)

        regions = _wait_for_layout(client, document_id)
        assert regions
        assert any(region["region_type"] in {"header", "body", "table"} for region in regions)
        assert all(0 <= region["confidence"] <= 1 for region in regions)
        assert all(region["document_id"] == document_id for region in regions)

    assert pipeline_events
    for index in range(0, len(pipeline_events), 2):
        assert pipeline_events[index:index + 2] == ["layout", "ocr"]


@pytest.mark.skipif(
    importlib.util.find_spec("layoutparser") is None
    or importlib.util.find_spec("detectron2") is None,
    reason="PubLayNet integration test requires layoutparser and detectron2",
)
def test_real_layout_model_on_three_document_types():
    """Run the actual PubLayNet adapter when its optional backend is installed."""
    from app.services.layout_detection_service import detect_layout

    sample_dir = os.path.join(os.path.dirname(__file__), ".layout_model_samples")
    os.makedirs(sample_dir, exist_ok=True)
    try:
        for label in ("prescription", "lab report", "discharge summary"):
            image_path = os.path.join(sample_dir, f"{label.replace(' ', '_')}.png")
            with open(image_path, "wb") as sample:
                sample.write(_sample_image_bytes(label))
            regions = detect_layout(image_path)

            assert regions
            assert any(region["type"] in {"header", "body", "table"} for region in regions)
            assert all(len(region["bbox"]) == 4 for region in regions)
            assert all(0 <= region["confidence"] <= 1 for region in regions)
    finally:
        shutil.rmtree(sample_dir, ignore_errors=True)
