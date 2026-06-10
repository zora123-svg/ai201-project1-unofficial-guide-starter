"""
Stage 1 of the pipeline: LOAD.

Reads every supported file in documents/ and extracts its text into a
consistent plain-text form, saving one .txt per source under data/raw/.

We deliberately do NOT clean here. For HTML files the "raw text" still
contains the HTML markup (tags, nav, boilerplate) -- removing that is the
job of Stage 2 (cleaner.py). Keeping the stages separate lets us inspect
the output of each one, which is the point of Milestone 3.

Supported file types:
    .pdf            -> text extracted with pdfplumber
    .html / .htm    -> raw HTML kept as-is (cleaned later)
    .txt / .md      -> read as-is

Run directly to load everything and print a summary:
    python -m src.loader
"""

from pathlib import Path

import pdfplumber

# Folder that holds the original source files you collected.
DOCUMENTS_DIR = Path("documents")
# Where extracted raw text is written, one .txt per source.
RAW_DIR = Path("data/raw")

# Extensions we know how to load. Anything else is skipped with a warning.
SUPPORTED_EXTENSIONS = {".pdf", ".html", ".htm", ".txt", ".md"}


def extract_text(path: Path) -> str:
    """Return the text content of a single source file.

    For PDFs we run pdfplumber page by page. For everything else we read the
    file as UTF-8 text (HTML markup is preserved and stripped later).
    """
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                # extract_text() returns None for image-only pages.
                pages.append(page.extract_text() or "")
        return "\n".join(pages)

    # .html / .htm / .txt / .md  -> read bytes and decode as UTF-8.
    # errors="ignore" drops the occasional bad byte instead of crashing.
    return path.read_text(encoding="utf-8", errors="ignore")


def load_documents() -> list[dict]:
    """Load every supported file in DOCUMENTS_DIR.

    Returns a list of dicts: {"source": <filename>, "raw_text": <str>}.
    Also writes each document's raw text to data/raw/<name>.txt so it can
    be inspected on disk.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    documents = []
    for path in sorted(DOCUMENTS_DIR.iterdir()):
        # Skip directories and the .gitkeep placeholder.
        if path.is_dir() or path.name == ".gitkeep":
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"  ! skipping unsupported file: {path.name}")
            continue

        text = extract_text(path)
        documents.append({"source": path.name, "raw_text": text})

        # Save a raw .txt copy for inspection / reproducibility.
        out_path = RAW_DIR / (path.stem + ".txt")
        out_path.write_text(text, encoding="utf-8")

    return documents


if __name__ == "__main__":
    docs = load_documents()
    print(f"\nLoaded {len(docs)} documents into '{RAW_DIR}/':\n")
    print(f"  {'SOURCE':<42} {'CHARS':>10}")
    print(f"  {'-' * 42} {'-' * 10}")
    for d in docs:
        print(f"  {d['source']:<42} {len(d['raw_text']):>10,}")
    total = sum(len(d["raw_text"]) for d in docs)
    print(f"  {'-' * 42} {'-' * 10}")
    print(f"  {'TOTAL':<42} {total:>10,}")
