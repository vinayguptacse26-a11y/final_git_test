Project: Emesh RAG prototype

This repository contains a small Retrieval-Augmented Generation (RAG) prototype named Emesh. It includes:

- ingestion.py: scripts to load and preprocess CSV data into tokenized documents
- retriever.py: a simple retriever wrapper that loads persisted indexes
- rag_engine.py: orchestrates retrieval and generation for RAG-style Q&A
- test_rag.py: pytest-based unit tests for basic integration

Repository notes and decisions applied by the AI DevOps Engineer:

- .env was detected and classified as SECRET; it is excluded from staging and committed files and added to .gitignore.
- Binary index files and pickled retriever artifacts are ignored to avoid large files in Git history (.faiss, .pkl).
- CSV files under Emesh/data appear to be small source data and are retained in the repository.

How to run:

1. Create a Python virtual environment: python -m venv .venv
2. Install dependencies: pip install -r Emesh/requirements.txt
3. Run tests: pytest -q

If you need this repository pushed to GitHub main branch with history transplant, provide the remote URL and confirm push intent.