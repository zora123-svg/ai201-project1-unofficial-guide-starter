"""
Milestone 4, Stage 2: RETRIEVE.

Embeds a query with the same model used for the chunks and returns the top-k
most similar chunks from ChromaDB, each with its source and cosine distance.

Run directly to test retrieval against the planning.md evaluation questions:
    python -m src.retriever
"""

import chromadb

from src.embed import CHROMA_PATH, COLLECTION_NAME, get_model

TOP_K = 5  # tuned up from 4: at k=4 some relevant chunks (e.g. the Midway
           # Reddit thread, rank 5 @ 0.347) were just missed; see planning.md.

# The 5 evaluation questions from planning.md.
EVAL_QUERIES = [
    "How many days does a landlord in Minnesota have to return my security deposit after I move out?",
    "Are there rules on how much my rent can be raised each year in St. Paul?",
    "Which neighborhoods near University of St. Thomas are popular with students and considered safe?",
    "What is the Student Tenant Education Program (STEP) and why would I take it?",
    "What do students or residents say about renting in the Midway area of St. Paul?",
]

_collection: chromadb.Collection | None = None


def get_collection() -> chromadb.Collection:
    """Open (once) the persistent ChromaDB collection built by embed.py."""
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Return the top-k chunks for a query, sorted by ascending distance."""
    model = get_model()
    collection = get_collection()

    query_embedding = model.encode([query]).tolist()
    result = collection.query(query_embeddings=query_embedding, n_results=k)

    hits = []
    for text, meta, dist in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        hits.append({
            "text": text,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "distance": dist,
        })
    return hits


if __name__ == "__main__":
    for query in EVAL_QUERIES:
        print("=" * 100)
        print(f"QUERY: {query}\n")
        for rank, hit in enumerate(retrieve(query), 1):
            preview = hit["text"][:260].replace("\n", " ")
            print(f"  [{rank}] distance={hit['distance']:.3f}  source={hit['source']}")
            print(f"      {preview}...\n")
