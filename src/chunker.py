"""
Stage 3 of the pipeline: CHUNK.

Splits each cleaned document into overlapping chunks sized for the
all-MiniLM-L6-v2 embedding model, following the strategy in planning.md:

    chunk size : ~500 characters
    overlap    : 100 characters (~20%)

A plain character window would cut sentences (and legal rules) in half, so
this chunker snaps each cut back to the nearest sentence boundary within a
small search window. Each chunk keeps its source filename as metadata so we
can cite it later and detect chunks attributed to the wrong document.

Run directly to chunk everything, save data/chunks.json, and inspect output:
    python -m src.chunker
"""

import json
import re
from pathlib import Path

from src.cleaner import clean_documents
from src.loader import load_documents

CHUNKS_PATH = Path("data/chunks.json")

CHUNK_SIZE = 500       # target characters per chunk
OVERLAP = 100          # characters shared between consecutive chunks
# How far back from the target cut we'll look for a sentence boundary.
BOUNDARY_SEARCH = 120

# A sentence/paragraph boundary: . ! ? or newline, optionally followed by
# closing quotes/brackets, then whitespace.
_BOUNDARY_RE = re.compile(r"[.!?\n][\"')\]]?\s")


def _find_boundary(text: str, start: int, target_end: int) -> int:
    """Return a cut point at or before target_end, snapped to a sentence end.

    Looks for the last sentence boundary in the window
    [target_end - BOUNDARY_SEARCH, target_end]. Falls back to target_end if
    no boundary is found (e.g. a very long run-on line).
    """
    window_start = max(start, target_end - BOUNDARY_SEARCH)
    window = text[window_start:target_end]
    matches = list(_BOUNDARY_RE.finditer(window))
    if matches:
        # End of the matched boundary, mapped back to absolute index.
        return window_start + matches[-1].end()
    return target_end


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = OVERLAP) -> list[str]:
    """Split one document's text into overlapping, sentence-aware chunks."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        target_end = min(start + chunk_size, n)
        # Only snap to a boundary if we're not already at the end of the text.
        end = target_end if target_end == n else _find_boundary(text, start, target_end)

        chunk = text[start:end].strip()
        if chunk:  # never emit empty/whitespace-only chunks
            chunks.append(chunk)

        if end >= n:
            break

        # Step forward, leaving `overlap` characters shared with the next chunk.
        next_start = end - overlap
        # Guard against the window failing to advance (would loop forever).
        start = next_start if next_start > start else end

    return chunks


def chunk_documents(cleaned_docs: list[dict]) -> list[dict]:
    """Chunk every cleaned document, attaching source metadata to each chunk.

    Exact-duplicate chunks are dropped. Some sources (e.g. apartment listing
    sites) repeat the same text many times; identical chunks add no new
    information and would otherwise flood retrieval results with duplicates,
    crowding out more relevant content from other sources.
    """
    all_chunks = []
    seen: set[str] = set()
    for doc in cleaned_docs:
        pieces = chunk_text(doc["text"])
        for i, piece in enumerate(pieces):
            key = " ".join(piece.split()).lower()  # normalise whitespace/case
            if key in seen:
                continue
            seen.add(key)
            all_chunks.append({
                "id": f"{Path(doc['source']).stem}-{i}",
                "source": doc["source"],
                "chunk_index": i,
                "text": piece,
            })
    return all_chunks


def build_chunks() -> list[dict]:
    """Run the full load -> clean -> chunk pipeline and save chunks.json."""
    docs = load_documents()
    cleaned = clean_documents(docs)
    chunks = chunk_documents(cleaned)

    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_PATH.write_text(json.dumps(chunks, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    return chunks


if __name__ == "__main__":
    chunks = build_chunks()

    # ---- Summary: per-source counts and overall stats ----
    print(f"\nProduced {len(chunks)} chunks (saved to {CHUNKS_PATH}).\n")

    per_source: dict[str, int] = {}
    for c in chunks:
        per_source[c["source"]] = per_source.get(c["source"], 0) + 1
    print(f"  {'SOURCE':<42} {'CHUNKS':>7}")
    print(f"  {'-' * 42} {'-' * 7}")
    for source, count in per_source.items():
        print(f"  {source:<42} {count:>7}")

    lengths = [len(c["text"]) for c in chunks]
    print(f"\n  chunk length: min={min(lengths)}  "
          f"avg={sum(lengths)//len(lengths)}  max={max(lengths)}")
    empties = sum(1 for L in lengths if L == 0)
    print(f"  empty chunks: {empties}")
