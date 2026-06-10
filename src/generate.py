"""
Milestone 5: GROUNDED GENERATION.

Connects retrieval to Groq's LLM. Retrieves the top-k chunks for a question,
filters out weak matches, and asks the model to answer using ONLY that
context. Source attribution is guaranteed programmatically: the returned
sources come from the retrieved chunks' metadata, not from the model's text.

Grounding is enforced two ways:
  1. A strict system prompt: answer only from context, decline otherwise.
  2. A distance filter: chunks above MAX_DISTANCE are dropped before the
     prompt is built. For an out-of-corpus question every chunk is a weak
     match, so no context survives and the model is told to decline.

Run directly to test end-to-end on the eval queries plus an out-of-corpus one:
    python -m src.generate
"""

import os

from dotenv import load_dotenv
from groq import Groq

from src.retriever import EVAL_QUERIES, TOP_K, retrieve

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
# Cosine distance above which a chunk is treated as not relevant enough to
# ground an answer. Calibrated against observed scores: real matches land
# ~0.25-0.46, off-topic content ~0.6+.
MAX_DISTANCE = 0.65

SYSTEM_PROMPT = (
    "You are the Unofficial Guide to off-campus housing for University of "
    "St. Thomas students in St. Paul, MN. Answer the user's question using "
    "ONLY the information in the provided context excerpts. Follow these "
    "rules strictly:\n"
    "1. Do not use any outside or prior knowledge. If the context does not "
    "contain enough information to answer, reply exactly: "
    "\"I don't have enough information on that.\"\n"
    "2. Do not guess, infer beyond the text, or fill gaps with general "
    "knowledge.\n"
    "3. Base every statement on the excerpts. Quote or paraphrase them.\n"
    "4. Keep the answer concise and specific to what the excerpts say."
)

_client: Groq | None = None


def get_client() -> Groq:
    """Create (once) the Groq client from the GROQ_API_KEY in .env."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_key_here":
            raise RuntimeError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add "
                "your key from https://console.groq.com."
            )
        _client = Groq(api_key=api_key)
    return _client


def build_context(hits: list[dict]) -> str:
    """Format retrieved chunks into a numbered, source-labelled context block."""
    blocks = []
    for i, hit in enumerate(hits, 1):
        blocks.append(f"[Excerpt {i} | source: {hit['source']}]\n{hit['text']}")
    return "\n\n".join(blocks)


def ask(question: str, k: int = TOP_K) -> dict:
    """Answer a question grounded in retrieved chunks.

    Returns {"answer": str, "sources": list[str], "hits": list[dict]}.
    """
    hits = retrieve(question, k=k)
    # Keep only chunks that are relevant enough to ground an answer.
    relevant = [h for h in hits if h["distance"] <= MAX_DISTANCE]

    if not relevant:
        return {
            "answer": "I don't have enough information on that.",
            "sources": [],
            "hits": hits,
        }

    context = build_context(relevant)
    user_prompt = (
        f"Context excerpts:\n\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the excerpts above."
    )

    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,  # low: stay close to the source text
    )
    answer = response.choices[0].message.content.strip()

    # If the model declined (context didn't actually support an answer), show
    # no sources -- listing sources next to a non-answer is misleading.
    if "don't have enough information" in answer.lower():
        return {"answer": answer, "sources": [], "hits": relevant}

    # Source attribution is programmatic: unique sources of the chunks we
    # actually fed to the model, preserving retrieval order.
    sources = list(dict.fromkeys(h["source"] for h in relevant))

    return {"answer": answer, "sources": sources, "hits": relevant}


if __name__ == "__main__":
    # Test the 5 eval queries plus an out-of-corpus question (grounding check).
    queries = EVAL_QUERIES + [
        "What are the best pizza restaurants in New York City?",
    ]
    for q in queries:
        result = ask(q)
        print("=" * 100)
        print(f"Q: {q}\n")
        print(f"A: {result['answer']}\n")
        print(f"Sources: {result['sources'] or '(none — declined)'}")
        print()
