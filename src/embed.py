"""
Milestone 4, Stage 1: EMBED + STORE.

Loads the chunks produced by the Milestone 3 pipeline, embeds them with the
all-MiniLM-L6-v2 sentence-transformer (local, no API key), and stores them in
a persistent ChromaDB collection with source metadata for later attribution.

The collection uses cosine distance, so scores run from 0 (identical) to 2
(opposite). Lower is better; the Milestone 4 checkpoint wants top results
below ~0.5.

Run directly to (re)build the index:
    python -m src.embed
"""

import json

import chromadb
from sentence_transformers import SentenceTransformer

from src.chunker import CHUNKS_PATH, build_chunks

MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_PATH = "chroma_db"          # gitignored local vector store
COLLECTION_NAME = "unofficial_guide"

# Cache the model so embed + retrieve in one process don't reload it.
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Load (once) and return the embedding model."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def load_chunks() -> list[dict]:
    """Read chunks from data/chunks.json, building them first if missing."""
    if CHUNKS_PATH.exists():
        return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    return build_chunks()


def build_index() -> chromadb.Collection:
    """Embed every chunk and (re)create the ChromaDB collection."""
    chunks = load_chunks()
    model = get_model()

    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks with {MODEL_NAME} ...")
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Start fresh each build so re-runs don't duplicate or stale-out chunks.
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=[
            {"source": c["source"], "chunk_index": c["chunk_index"]}
            for c in chunks
        ],
    )
    print(f"Stored {collection.count()} chunks in collection "
          f"'{COLLECTION_NAME}' at '{CHROMA_PATH}/'.")
    return collection


if __name__ == "__main__":
    build_index()
