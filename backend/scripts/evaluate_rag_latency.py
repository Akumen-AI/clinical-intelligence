#!/usr/bin/env python3
import time
import uuid
import numpy as np
from sqlalchemy.orm import Session
import os
import sys

# Add the backend directory to the Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from app.database import SessionLocal

def evaluate_latency():
    db: Session = SessionLocal()
    patient_id = "test-latency-patient"
    
    # We just want to measure retrieval latency, so we can mock or use a real patient
    # Actually query_patient_record calls generate_answer which calls retrieve_relevant_chunks
    # Let's measure generate_answer directly!
    from app.services.rag_service import generate_answer
    
    latencies = []
    print("Warming up RAG latency monitoring...")
    try:
        generate_answer(db, patient_id, "test query", str(uuid.uuid4()))
    except Exception:
        pass
        
    print("Measuring RAG latency for 20 requests...")
    for _ in range(20):
        start = time.perf_counter()
        try:
            generate_answer(db, patient_id, "what is the patient's condition?", str(uuid.uuid4()))
        except Exception:
            pass
        end = time.perf_counter()
        latencies.append((end - start) * 1000) # in ms
        
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    
    print("\n--- RAG Retrieval Latency Report ---")
    print(f"p50 Latency: {p50:.2f} ms")
    print(f"p95 Latency: {p95:.2f} ms")
    print(f"p99 Latency: {p99:.2f} ms")
    print("------------------------------------")

if __name__ == "__main__":
    evaluate_latency()
