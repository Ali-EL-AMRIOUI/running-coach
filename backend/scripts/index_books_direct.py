#!/usr/bin/env python3
"""
scripts/index_books_direct.py
Indexing 9 books in Qdrant with:
- Text extraction: pdfplumber + ebooklib
- Intelligent chunking: LangChain RecursiveCharacterTextSplitter
- Dense embedding: Infinity + BAAI/bge-m3 (1024 dimensions)
- Sparse embedding: BAAI/bge-m3 sparse (BM25-like) via Infinity
- Storage: Qdrant Cloud with hybrid collection
"""

import os
import sys
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    Distance,
    PointStruct,
    HnswConfigDiff,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

# CONFIG
# ------------------------------------------------------------
INFINITY_URL    = os.getenv("INFINITY_URL", "http://localhost:7997")
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM   = 1024

QDRANT_URL      = os.getenv("QDRANT_URL")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "running_knowledge"

BOOKS_DIR = Path(__file__).parent.parent.parent / "data" / "books"
CHUNK_SIZE      = 800
CHUNK_OVERLAP   = 200
BATCH_SIZE      = 32


# DENSE + SPARSE EMBEDDING via Infinity
# ------------------------------------------------------------

def embed_dense(texts: list[str]) -> list[list[float]]:
    """Dense embedding via Infinity + bge-m3 (1024 dims)."""
    response = requests.post(
        f"{INFINITY_URL}/embeddings",
        json={"input": texts, "model": EMBEDDING_MODEL},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    sorted_data = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in sorted_data]


def embed_sparse(texts: list[str]) -> list[dict]:
    """
    Sparse embedding via Infinity + bge-m3 sparse.
    Returns sparse vectors {indices: [...], values: [...]}.
    """
    try:
        response = requests.post(
            f"{INFINITY_URL}/embeddings",
            json={
                "input": texts,
                "model": EMBEDDING_MODEL,
                "encoding_format": "float",
                "modality": "text",
                "extra_options": {"return_sparse": True},
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        sparse_results = []
        for item in sorted_data:
            sparse = item.get("sparse_embedding", {})
            if sparse:
                sparse_results.append({
                    "indices": sparse.get("indices", []),
                    "values": sparse.get("values", []),
                })
            else:
                sparse_results.append(None)
        return sparse_results
    except Exception as e:
        print(f"   Sparse embedding not available: {e}")
        return [None] * len(texts)


# TEXT EXTRACTION
# ------------------------------------------------------------

def pdf_to_text(pdf_path: str) -> str:
    import pdfplumber
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                texts.append(text)
    return "\n\n".join(texts)


def epub_to_text(epub_path: str) -> str:
    from ebooklib import epub
    from bs4 import BeautifulSoup
    book = epub.read_epub(epub_path)
    texts = []
    for item in book.get_items():
        if item.get_type() == 9:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n")
            if text.strip():
                texts.append(text)
    return "\n\n".join(texts)


def extract_text(file_path: Path) -> str:
    if file_path.suffix.lower() == ".pdf":
        return pdf_to_text(str(file_path))
    elif file_path.suffix.lower() == ".epub":
        return epub_to_text(str(file_path))
    return ""


# INTELLIGENT CHUNKING
# ------------------------------------------------------------

def chunk_text(text: str, source: str) -> list[dict]:
    """
    Splits text into intelligent chunks.
    Cuts on paragraphs and sentences - never in the middle of a word.
    200 char overlap to preserve context between chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "! ", "? ", " "],
        length_function=len,
    )
    chunks = splitter.split_text(text)
    chunks = [c.strip() for c in chunks if len(c.strip()) >= 100]
    return [
        {"content": chunk, "source": source, "chunk_index": i}
        for i, chunk in enumerate(chunks)
    ]


# QDRANT SETUP - Hybrid Collection
# ------------------------------------------------------------

def setup_qdrant_collection(client: QdrantClient):
    """
    Creates Qdrant collection with:
    - Dense vectors (bge-m3, 1024 dims) for semantic search
    - Sparse vectors (BM25-like) for keyword search
    -> Hybrid Search possible via RRF
    """
    try:
        client.delete_collection(COLLECTION_NAME)
        print("Old collection deleted")
        time.sleep(2)
    except Exception:
        pass

    client.create_collection(
        collection_name=COLLECTION_NAME,
        # Dense vectors
        vectors_config={
            "dense": VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        },
        # Sparse vectors for BM25
        sparse_vectors_config={
            "sparse": SparseVectorParams(
                index=SparseIndexParams(
                    on_disk=False,
                ),
            ),
        },
        # HNSW optimized for precision
        hnsw_config=HnswConfigDiff(
            m=16,
            ef_construct=200,
        ),
    )
    print(f"Collection '{COLLECTION_NAME}' created")
    print(f"   Dense  : {EMBEDDING_DIM} dims (BAAI/bge-m3)")
    print(f"   Sparse : BM25-like (BAAI/bge-m3 sparse)")


# MAIN
# ------------------------------------------------------------

def main():
    print("=" * 60)
    print("QDRANT INDEXING - Hybrid (Dense + Sparse)")
    print(f"   Model  : {EMBEDDING_MODEL}")
    print(f"   Server : {INFINITY_URL}")
    print("=" * 60)

    # Check Infinity
    print("\nChecking Infinity...")
    try:
        r = requests.get(f"{INFINITY_URL}/models", timeout=5)
        r.raise_for_status()
        models = [m["id"] for m in r.json().get("data", [])]
        print(f"Infinity operational - models: {models}")
    except Exception as e:
        print(f"Infinity not accessible: {e}")
        print("   Run: infinity_emb v2 --model-id BAAI/bge-m3 --port 7997 --no-bettertransformer")
        sys.exit(1)

    # Qdrant connection
    print("\nConnecting to Qdrant...")
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=300,
    )
    print("Qdrant connected")

    # Setup hybrid collection
    setup_qdrant_collection(client)

    # List books
    files = [
        f for f in BOOKS_DIR.glob("*.*")
        if f.suffix.lower() in (".pdf", ".epub")
        and "Zone.Identifier" not in str(f)
    ]
    print(f"\n{len(files)} books found")
    for f in files:
        print(f"   Book: {f.name}")

    # Extraction + Chunking
    print("\nExtraction and chunking...")
    all_chunks = []
    for file_path in files:
        print(f"\n   {file_path.name}")
        try:
            text = extract_text(file_path)
            if not text.strip():
                print(f"      Empty content - skipped")
                continue
            print(f"      {len(text):,} characters")
            chunks = chunk_text(text, file_path.name)
            print(f"      {len(chunks)} chunks")
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"      Error: {e}")

    print(f"\nTotal: {len(all_chunks)} chunks")

    # Embedding + Upload by batches
    print(f"\nEmbedding + Upload (batch={BATCH_SIZE})...")
    total_batches = (len(all_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    total_uploaded = 0

    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch       = all_chunks[i:i + BATCH_SIZE]
        batch_num   = i // BATCH_SIZE + 1
        texts       = [c["content"] for c in batch]

        try:
            # Dense embeddings
            dense_vecs  = embed_dense(texts)

            # Sparse embeddings (optional)
            sparse_vecs = embed_sparse(texts)

            # Build Qdrant points
            points = []
            for j, (chunk, dense) in enumerate(zip(batch, dense_vecs)):
                point_id = i + j
                vectors  = {"dense": dense}

                # Add sparse if available
                sparse = sparse_vecs[j] if sparse_vecs else None
                if sparse and sparse.get("indices"):
                    vectors["sparse"] = sparse

                points.append(PointStruct(
                    id=point_id,
                    vector=vectors,
                    payload={
                        "source":      chunk["source"],
                        "chunk_index": chunk["chunk_index"],
                        "content":     chunk["content"],
                    },
                ))

            # Upload to Qdrant
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
            )
            total_uploaded += len(points)
            print(f"   Batch {batch_num}/{total_batches} - {len(points)} points uploaded")

        except Exception as e:
            print(f"   Error batch {batch_num}: {e}")
            time.sleep(2)

    # Final summary
    info = client.get_collection(COLLECTION_NAME)
    print("\n" + "=" * 60)
    print("INDEXING COMPLETE")
    print(f"   Collection     : {COLLECTION_NAME}")
    print(f"   Points indexed : {info.points_count}")
    print(f"   Dense dim      : {EMBEDDING_DIM} (BAAI/bge-m3)")
    print(f"   Sparse         : BM25-like enabled")
    print(f"   Hybrid Search  : ready")
    print("=" * 60)


if __name__ == "__main__":
    main()