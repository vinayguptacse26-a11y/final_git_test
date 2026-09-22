from pathlib import Path
import pickle
import faiss
import numpy as np
import logging

logger = logging.getLogger(__name__)

class IndexWriter:
    """
    Writes or appends FAISS index and metadata to disk.
    Handles dynamic folder creation for new indices.
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)

    def write(
        self,
        chunks,
        embeddings,
        index_name: str
    ):
        if not chunks:
            logger.warning("No chunks provided. Skipping index write.")
            return

     
        index_dir = self.base_dir / index_name
        index_dir.mkdir(parents=True, exist_ok=True)
        
        index_file = index_dir / "index.faiss"
        metadata_file = index_dir / "metadata.pkl"

        new_embeddings = np.array(embeddings).astype("float32")
        dim = new_embeddings.shape[1]

        if index_file.exists() and metadata_file.exists():
            logger.info("Updating existing index: '%s'", index_name)
            index = faiss.read_index(str(index_file))
            
            with open(metadata_file, "rb") as f:
                existing_chunks = pickle.load(f)
            
            index.add(new_embeddings)
            final_chunks = existing_chunks + chunks
        else:
            logger.info("Creating new index folder: '%s'", index_name)
            index = faiss.IndexFlatL2(dim)
            index.add(new_embeddings)
            final_chunks = chunks

        
        faiss.write_index(index, str(index_file))
        with open(metadata_file, "wb") as f:
            pickle.dump(final_chunks, f)

        logger.info("Index updated at %s | Total chunks: %d", index_dir, len(final_chunks))