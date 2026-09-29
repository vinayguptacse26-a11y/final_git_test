Emesh: CSV Hybrid RAG

This repository contains a small Python project that builds a hybrid retrieval system
on top of CSV data using a combination of FAISS (dense vector search) and BM25 (sparse keyword search).

Key components:
- Emesh/ingestion.py: Reads CSV files and builds FAISS and BM25 indexes.
- Emesh/retriever.py: Loads the saved indexes and composes an EnsembleRetriever.
- Emesh/rag_engine.py: Provides CSVHybridRAG, a simple interface to query the RAG system.
- Emesh/test_rag.py: Example script to exercise ingestion and querying.

Notes & Safety:
- The repository contains an Emesh/.env file which is treated as SECRET and will not be committed.
- Index artifacts (faiss index, pickled retriever) are ignored in the .gitignore so they are not accidentally committed.

Quickstart
1. Create a Python virtual environment and install requirements:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r Emesh/requirements.txt

2. Populate CSV files in Emesh/data/ matching the filenames used in ingestion.py (or edit ingestion.py to point to your CSVs).

3. Run the ingestion script to build indexes:
   python Emesh/ingestion.py

4. To query via the RAG engine, set GROQ_API_KEY in Emesh/.env or your shell environment, then use the CSVHybridRAG class.

