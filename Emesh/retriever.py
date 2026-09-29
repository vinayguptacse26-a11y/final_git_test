import os
import pickle
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.retrievers import EnsembleRetriever

def load_hybrid_retriever(index_dir: str, faiss_weight: float = 0.5, bm25_weight: float = 0.5):
    """
    Loads the saved FAISS and BM25 indexes from disk and combines them into 
    an EnsembleRetriever (Hybrid Search) using Reciprocal Rank Fusion (RRF).
    
    Args:
        index_dir: Directory where the indexes are saved.
        faiss_weight: Weight given to semantic (vector) search results.
        bm25_weight: Weight given to exact keyword (sparse) search results.
        
    Returns:
        An EnsembleRetriever instance ready to be used in a LangChain pipeline.
    """
    faiss_index_path = os.path.join(index_dir, "faiss_index")
    bm25_index_path = os.path.join(index_dir, "bm25_retriever.pkl")
    
    if not os.path.exists(faiss_index_path) or not os.path.exists(bm25_index_path):
        raise FileNotFoundError(f"Indexes not found in {index_dir}. Please run ingestion.py first.")
        
    # 1. Load FAISS (Dense Retriever)
    # We must use the same embedding model used during ingestion
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # allow_dangerous_deserialization=True is required for FAISS in newer Langchain versions
    # when loading local files you trust.
    faiss_vectorstore = FAISS.load_local(
        folder_path=faiss_index_path, 
        embeddings=embeddings, 
        allow_dangerous_deserialization=True
    )
    
    # Convert vectorstore to retriever (can adjust k=top_k here)
    faiss_retriever = faiss_vectorstore.as_retriever(search_kwargs={"k": 5})
    
    # 2. Load BM25 (Sparse Retriever)
    with open(bm25_index_path, "rb") as f:
        bm25_retriever = pickle.load(f)
        
    # Optional: configure BM25 top_k
    bm25_retriever.k = 5
    
    # 3. Combine into an EnsembleRetriever (Hybrid Search)
    ensemble_retriever = EnsembleRetriever(
        retrievers=[faiss_retriever, bm25_retriever],
        weights=[faiss_weight, bm25_weight]
    )
    
    return ensemble_retriever

if __name__ == "__main__":
    # Example usage:
    # retriever = load_hybrid_retriever("indexes/")
    # results = retriever.invoke("search query")
    # print(results)
    pass
