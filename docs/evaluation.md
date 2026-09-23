# Evaluation

The Clinical Intelligence Platform includes a suite of evaluation tools located in `backend/scripts/`.

## Running Evaluations

### 1. RAG Latency & Accuracy
Evaluates the vector retrieval pipeline latency and standard deviation.
```bash
cd backend
python scripts/evaluate_rag_latency.py
```

### 2. Handwriting Extraction
Evaluates the multimodal extraction capabilities against synthetic handwriting samples.
```bash
cd backend
python scripts/evaluate_handwriting_extraction.py
```

## Reviewing Results
All evaluation outputs are saved as JSON artifacts in the `backend/eval_reports/` directory. These reports contain granular metrics such as execution time, accuracy rates, and latency breakdowns to help guide performance improvements.
