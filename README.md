Project: RAG Assignment (Vinay)

This repository contains a Retrieval-Augmented Generation (RAG) project written in Python. The codebase provides ingestion, chunking, retrieval (BM25 and vector), and a pipeline to serve RAG-based APIs.

Key components:
- app/ingestion: loaders and chunkers for PDFs, DOCX, PPTX
- app/retrieval: bm25, dense, hybrid retrieval implementations
- app/pipeline: rag_pipeline orchestration
- app/src: core utilities (embedder, llm_client, index_writer, etc.)
- frontend: a simple static UI for quick testing

Notes for maintainers:
- This repo contains potentially large data files and a .env with secrets in the RAG(Assignment 2 done) directory. These are intentionally left out of commits via .gitignore.
- To run locally: create a virtualenv and install via pip install -r "RAG(Assignment 2 done)/requirements.txt".
- Index files are generated in app/indexes and should not be committed.
