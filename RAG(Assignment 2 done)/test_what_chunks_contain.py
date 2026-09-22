"""
Run this script to see exactly what page metadata your ingestion pipeline writes.
This will tell us if the bug is in the loader or the citation extractor.

Usage:
  python test_what_chunks_contain.py

It will load your FAISS index and print the raw metadata from the first 10 chunks.
"""
import pickle
from pathlib import Path

index_dir = Path("app/indexes/vector_index")
metadata_file = index_dir / "metadata.pkl"

if not metadata_file.exists():
    print(f"ERROR: {metadata_file} not found")
    print("Make sure you run this from your project root directory")
    exit(1)

with open(metadata_file, "rb") as f:
    metadata = pickle.load(f)

print(f"Loaded {len(metadata)} chunks from {metadata_file}")
print("=" * 70)

for i, chunk in enumerate(metadata[:10]):
    print(f"\n[Chunk {i}]")
    
    # Show all keys
    if isinstance(chunk, dict):
        chunk_dict = chunk
        meta = chunk.get("metadata", {}) if isinstance(chunk.get("metadata"), dict) else {}
    else:
        chunk_dict = vars(chunk) if hasattr(chunk, "__dict__") else {}
        meta = chunk_dict.get("metadata", {}) if isinstance(chunk_dict.get("metadata"), dict) else {}
    
    # Filename
    filename = (meta.get("filename") or meta.get("source") or meta.get("file_name") or
                chunk_dict.get("filename") or chunk_dict.get("source") or "?")
    print(f"  filename: {filename}")
    
    # ALL page-related fields
    page_fields_meta = {k: v for k, v in meta.items() 
                        if any(x in k.lower() for x in ["page", "slide", "block"])}
    page_fields_flat = {k: v for k, v in chunk_dict.items() 
                        if any(x in k.lower() for x in ["page", "slide", "block"]) 
                        and k != "metadata"}
    
    if page_fields_meta:
        print(f"  page fields in metadata: {page_fields_meta}")
    if page_fields_flat:
        print(f"  page fields flat:        {page_fields_flat}")
    
    if not page_fields_meta and not page_fields_flat:
        print(f"  ❌ NO PAGE FIELDS AT ALL")
    
    # Text preview
    text = chunk_dict.get("text") or chunk_dict.get("content") or ""
    print(f"  text preview: {str(text)[:100]}...")

print("\n" + "=" * 70)
print("\nDIAGNOSIS:")
print("  If you see page=0 or page_number=0 for ALL chunks:")
print("    → Your loader sets page once and never updates it")
print("  If you see NO PAGE FIELDS:")
print("    → Your loader doesn't write page metadata at all")
print("  If you see correct page numbers (0, 1, 2, 3...):")
print("    → Loader is correct, citation extractor has a bug")