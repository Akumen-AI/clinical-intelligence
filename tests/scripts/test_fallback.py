import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import app.services.classification.factory as factory

# Mock Ollama as unavailable
factory._is_ollama_available = lambda host="http://localhost:11434": False

def test():
    classifier = factory.get_document_classifier()
    print("Got classifier:", type(classifier).__name__)
    res = classifier.classify("Patient John Doe has a high fever. Please prescribe amoxicillin.")
    print("Result:", res)

if __name__ == '__main__':
    test()
