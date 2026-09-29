import os
from dotenv import load_dotenv
load_dotenv()

from ingestion import process_csv_and_build_indices
from rag_engine import CSVHybridRAG

def main():
    # 1. Setup Data & Index
    csv_file = "sample_data.csv"
    index_folder = "indexes"
    
    # We will only build the indexes if they don't already exist for this test
    if not os.path.exists(index_folder):
        print("=== Step 1: Ingesting CSV and Building Indexes ===")
        # We can specify which columns to index if we don't want all of them.
        # But by default, it will take all columns.
        process_csv_and_build_indices(csv_file, index_folder)
    else:
        print("Indexes already exist. Skipping ingestion.")
        
    # 2. Querying the RAG
    # Note: You MUST set GROQ_API_KEY in your environment for this to work.
    # e.g., os.environ["GROQ_API_KEY"] = "your_key_here"
    
    # If the user hasn't set it yet, we just gracefully warn them.
    if "GROQ_API_KEY" not in os.environ:
        print("\n[!] WARNING: GROQ_API_KEY environment variable is not set.")
        print("To run the Groq LLM generation, please export it in your terminal:")
        print("    set GROQ_API_KEY=your_key (on Windows)")
        print("    export GROQ_API_KEY=your_key (on Mac/Linux)")
        print("\nWe will skip the full LLM generation and just demonstrate the RAW retrieval...")
        
        # We can test the retriever directly without the LLM if there's no API key
        from retriever import load_hybrid_retriever
        retriever = load_hybrid_retriever(index_folder)
        query = "Show me the fitness products."
        docs = retriever.invoke(query)
        print(f"\nRaw retrieved docs for '{query}':")
        for d in docs:
            print(d.page_content)
            print("---")
        return

    print("\n=== Step 2: Initializing the CSV Hybrid RAG Engine ===")
    rag = CSVHybridRAG(index_dir=index_folder)
    
    queries = [
        "what are the common root causes?"
        
    ]
    
    for q in queries:
        print(f"\nQ: {q}")
        print("A: ", end="", flush=True)
        for chunk in rag.stream_query(q):
            print(chunk, end="", flush=True)
        print("\n")

if __name__ == "__main__":
    main()
