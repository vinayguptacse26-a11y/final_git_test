import os
import pickle
import pandas as pd

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever


def process_csv_and_build_indices(
    csv_paths: list,
    output_dir: str
):
    """
    Reads multiple CSV files, converts every row into a LangChain Document,
    and builds:

    1. FAISS index  -> Dense semantic search
    2. BM25 index   -> Sparse keyword search

    All CSV files are combined into the same indexes.

    Each document keeps metadata containing:
        - source CSV file
        - row index
        - original column values
    """

    # ---------------------------------------------------------
    # 1. Create output directory
    # ---------------------------------------------------------

    os.makedirs(output_dir, exist_ok=True)

    # This will contain documents from ALL CSV files
    documents = []

    # ---------------------------------------------------------
    # 2. Read all CSV files
    # ---------------------------------------------------------

    for csv_path in csv_paths:

        print("\n" + "=" * 60)
        print(f"Loading CSV: {csv_path}")
        print("=" * 60)

        # Check whether file exists
        if not os.path.exists(csv_path):
            print(f"WARNING: File not found: {csv_path}")
            continue

        # Read file based on extension
        if csv_path.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(csv_path)
        else:
            try:
                # sep=None allows Pandas to automatically detect whether it's comma, semicolon, or tab separated
                df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip', sep=None, engine='python')
            except UnicodeDecodeError:
                # Fallback for CSVs exported from Excel/Windows with special characters
                df = pd.read_csv(csv_path, encoding='cp1252', on_bad_lines='skip', sep=None, engine='python')

        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")

        # -----------------------------------------------------
        # 3. Convert every row into a Document
        # -----------------------------------------------------

        for idx, row in df.iterrows():

            row_text = []

            # Metadata
            metadata = {
                "source": os.path.basename(csv_path),
                "row_index": str(idx)
            }

            # Process every column in this CSV
            for col in df.columns:

                value = row[col]

                # Ignore empty values
                if pd.notna(value):

                    # Convert value to string
                    value = str(value)

                    # Add to text representation
                    row_text.append(
                        f"{col}: {value}"
                    )

                    # Store original value in metadata
                    metadata[col] = value

            # Combine all columns into one text block
            page_content = "\n".join(row_text)

            # Create LangChain Document
            document = Document(
                page_content=page_content,
                metadata=metadata
            )

            documents.append(document)

    # ---------------------------------------------------------
    # 4. Check whether documents were created
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print(f"Total documents created: {len(documents)}")
    print("=" * 60)

    if len(documents) == 0:
        raise ValueError(
            "No documents were created. "
            "Check your CSV file paths."
        )

    # ---------------------------------------------------------
    # 5. Initialize embedding model
    # ---------------------------------------------------------

    print("\nInitializing HuggingFace embedding model...")

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    print("Embedding model initialized.")

    # ---------------------------------------------------------
    # 6. Build FAISS Dense Index
    # ---------------------------------------------------------

    print("\nBuilding FAISS index...")

    faiss_vectorstore = FAISS.from_documents(
        documents,
        embeddings
    )

    faiss_index_path = os.path.join(
        output_dir,
        "faiss_index"
    )

    faiss_vectorstore.save_local(
        faiss_index_path
    )

    print(
        f"FAISS index saved to: {faiss_index_path}"
    )

    # ---------------------------------------------------------
    # 7. Build BM25 Sparse Index
    # ---------------------------------------------------------

    print("\nBuilding BM25 index...")

    bm25_retriever = BM25Retriever.from_documents(
        documents
    )

    bm25_index_path = os.path.join(
        output_dir,
        "bm25_retriever.pkl"
    )

    with open(
        bm25_index_path,
        "wb"
    ) as f:

        pickle.dump(
            bm25_retriever,
            f
        )

    print(
        f"BM25 index saved to: {bm25_index_path}"
    )

    # ---------------------------------------------------------
    # 8. Finished
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("INDEXING COMPLETE")
    print("=" * 60)

    print(f"Total documents: {len(documents)}")
    print(f"FAISS index: {faiss_index_path}")
    print(f"BM25 index: {bm25_index_path}")


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    # ---------------------------------------------------------
    # CSV files
    # ---------------------------------------------------------

    csv_files = [

        "data/AI_Risk_Insights 1.csv",

        "data/fact_batch_risk_score 1.csv",

        "data/fact_equipment_risk.csv",

        "data/fact_root_cause_prediction.csv"

    ]

    # ---------------------------------------------------------
    # Output directory
    # ---------------------------------------------------------

    output_directory = "indexes"

    # ---------------------------------------------------------
    # Build FAISS + BM25 indexes
    # ---------------------------------------------------------

    process_csv_and_build_indices(
        csv_paths=csv_files,
        output_dir=output_directory
    )