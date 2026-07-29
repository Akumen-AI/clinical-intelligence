import sys
import os
from app.services.classification.gemini_classifier import GeminiClassifier

def test():
    try:
        classifier = GeminiClassifier()
        print("Got classifier:", type(classifier).__name__)
        print("Model name:", classifier.model_name)
        res = classifier.classify("Patient John Doe has a high fever. Please prescribe amoxicillin.")
        print("Result:", res)
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test()
