"""
Stage 2 of the pipeline: CLEAN.

Takes the loaded documents and removes everything that is not substantive
content, then writes one cleaned .txt per source under data/clean/.

For HTML sources this means stripping tags, scripts, styles, navigation,
headers, and footers with BeautifulSoup, then collapsing whitespace.
For PDF/text sources it means normalising whitespace and unescaping any
stray HTML entities.

Run directly to clean everything and print a before/after summary:
    python -m src.cleaner
"""

import html
import re
from pathlib import Path

from bs4 import BeautifulSoup

from src.loader import load_documents

CLEAN_DIR = Path("data/clean")

# HTML elements that never contain content we want to keep.
BOILERPLATE_TAGS = [
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "button", "svg", "iframe", "input", "select",
]

# Filenames whose source was HTML (so we know to run the HTML cleaner).
HTML_SUFFIXES = {".html", ".htm"}


def clean_html(raw_html: str) -> str:
    """Strip an HTML document down to its readable text."""
    soup = BeautifulSoup(raw_html, "html.parser")

    # Drop whole subtrees that are navigation/scripts/etc.
    for tag in soup(BOILERPLATE_TAGS):
        tag.decompose()

    # get_text with a newline separator keeps block structure readable.
    text = soup.get_text(separator="\n")
    return normalise_whitespace(text)


def normalise_whitespace(text: str) -> str:
    """Unescape HTML entities and collapse runaway whitespace.

    - &amp; / &nbsp; -> their real characters
    - trim trailing spaces on each line
    - collapse 3+ blank lines down to a single blank line
    - drop empty lines left behind by removed tags
    """
    text = html.unescape(text)
    text = text.replace("\xa0", " ")  # non-breaking space -> normal space

    # Fix encoding artifacts from PDF extraction: the Unicode replacement
    # char (most often a curly apostrophe lost during extraction) and any
    # smart quotes that did survive -> plain ASCII equivalents.
    text = text.replace("�", "'")
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')

    # Remove "dot leader" runs from PDF tables of contents (e.g. ".....11").
    # 4+ dots (optionally spaced) become a single space; real ellipses (3) stay.
    text = re.sub(r"(?:\.\s*){4,}", " ", text)

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]  # drop blank lines

    text = "\n".join(lines)
    # Collapse runs of spaces/tabs inside a line.
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def clean_document(doc: dict) -> dict:
    """Clean one loaded document based on its original file type."""
    suffix = Path(doc["source"]).suffix.lower()
    if suffix in HTML_SUFFIXES:
        cleaned = clean_html(doc["raw_text"])
    else:
        # PDF text and plain text just need whitespace normalisation.
        cleaned = normalise_whitespace(doc["raw_text"])
    return {"source": doc["source"], "text": cleaned}


def clean_documents(documents: list[dict]) -> list[dict]:
    """Clean every document and write results to data/clean/."""
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    cleaned_docs = []
    for doc in documents:
        cleaned = clean_document(doc)
        cleaned_docs.append(cleaned)
        out_path = CLEAN_DIR / (Path(doc["source"]).stem + ".txt")
        out_path.write_text(cleaned["text"], encoding="utf-8")
    return cleaned_docs


if __name__ == "__main__":
    raw_docs = load_documents()
    cleaned_docs = clean_documents(raw_docs)

    print(f"\nCleaned {len(cleaned_docs)} documents into '{CLEAN_DIR}/':\n")
    print(f"  {'SOURCE':<42} {'RAW':>10} {'CLEAN':>10} {'KEPT':>6}")
    print(f"  {'-' * 42} {'-' * 10} {'-' * 10} {'-' * 6}")
    for raw, clean in zip(raw_docs, cleaned_docs):
        raw_len = len(raw["raw_text"])
        clean_len = len(clean["text"])
        pct = (clean_len / raw_len * 100) if raw_len else 0
        print(f"  {clean['source']:<42} {raw_len:>10,} {clean_len:>10,} {pct:>5.0f}%")
