import pytest
from unittest.mock import patch, MagicMock
import json

from app.services.classification.base import ClassificationResult
from app.services.classification.ollama_classifier import OllamaClassifier
from app.services.classification.gemini_classifier import GeminiClassifier
from app.services.classification.factory import get_document_classifier
from app.config import settings

def test_ollama_classifier_success(mocker):
    # Mock requests.post
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": json.dumps({"document_type": "Lab Report", "confidence": 0.95})
    }
    mocker.patch("requests.post", return_value=mock_response)
    
    classifier = OllamaClassifier()
    result = classifier.classify("mock text")
    
    assert result.document_type == "Lab Report"
    assert result.confidence == 0.95

def test_ollama_classifier_invalid_json(mocker):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": "invalid json"
    }
    mocker.patch("requests.post", return_value=mock_response)
    
    classifier = OllamaClassifier()
    result = classifier.classify("mock text")
    
    # Should fallback gracefully
    assert result.document_type == "Unknown"
    assert result.confidence == 0.0

def test_gemini_classifier_success(mocker):
    # Mock genai client
    mock_client = MagicMock()
    mock_generate = MagicMock()
    mock_generate.text = json.dumps({"document_type": "Discharge Summary", "confidence": 0.85})
    mock_client.models.generate_content.return_value = mock_generate
    
    mocker.patch("google.genai.Client", return_value=mock_client)
    
    classifier = GeminiClassifier(api_key="test_key")
    result = classifier.classify("mock text")
    
    assert result.document_type == "Discharge Summary"
    assert result.confidence == 0.85

def test_gemini_classifier_missing_key(mocker):
    mocker.patch.object(settings, 'GEMINI_API_KEY', None)
    with pytest.raises(ValueError):
        GeminiClassifier(api_key="")

def test_factory_gemini(mocker):
    mocker.patch.object(settings, 'AI_PROVIDER', 'gemini')
    mocker.patch.object(settings, 'GEMINI_API_KEY', 'test_key')
    
    classifier = get_document_classifier()
    assert isinstance(classifier, GeminiClassifier)

def test_factory_ollama(mocker):
    mocker.patch.object(settings, 'AI_PROVIDER', 'ollama')
    
    classifier = get_document_classifier()
    assert isinstance(classifier, OllamaClassifier)

def test_factory_fallback(mocker):
    mocker.patch.object(settings, 'AI_PROVIDER', 'unknown_provider')
    
    classifier = get_document_classifier()
    assert isinstance(classifier, OllamaClassifier)
