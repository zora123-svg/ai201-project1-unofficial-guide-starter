# The Unofficial Guide — Project 1

A retrieval-augmented (RAG) question-answering system over off-campus housing
knowledge for University of St. Thomas students in St. Paul, MN.

**Run it:**
```bash
pip install -r requirements.txt        # deps
cp .env.example .env                   # then add your GROQ_API_KEY
python -m src.embed                    # build the vector store (one time)
python app.py                          # open http://localhost:7860
```
Pipeline: `src/loader.py` → `src/cleaner.py` → `src/chunker.py` → `src/embed.py`
→ `src/retriever.py` → `src/generate.py`, with a Gradio UI in `app.py`.

---

## Domain

Off-campus housing for University of St. Thomas students (St. Paul, MN): what
it's actually like to rent near campus — which neighborhoods (Macalester-
Groveland, Highland Park, Midway) fit a student budget and commute, how
specific landlords and complexes treat tenants, and what Minnesota and St. Paul
rental law (deposit returns, the Rent Stabilization Ordinance, eviction notice)
means in practice. This knowledge is hard to find through official channels
because the university's listing portal shows price and availability but not
honest tenant experiences, while the candid warnings — bad landlords, hidden
fees, which blocks to avoid — are scattered across Reddit threads, review
sites, and government PDFs that no single source consolidates.

---

## Document Sources

12 documents collected into `documents/` and processed by the pipeline.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | MN Attorney General — Landlords & Tenants: Rights & Responsibilities | Legal / tenant rights | https://www.ag.state.mn.us/brochures/publandlordtenants.pdf → `documents/mn_ag_landlord_tenant.pdf` |
| 2 | City of St. Paul — Tenant Protections | Legal / tenant rights | https://www.stpaul.gov/departments/safety-inspections/rent-buy-sell-property/renting-property/tenant-protections |
| 3 | UST — Housing Resources | Official university guide | https://www.stthomas.edu/student-life/off-campus/housing-resources/ |
| 4 | UST — Programs & Services (STEP) | Official university guide | https://www.stthomas.edu/student-life/off-campus/programs-services/ |
| 5 | UST — Disclosures for Renters & Landlords | Official university guide | https://www.stthomas.edu/student-life/off-campus/housing-resources/disclosures-renters-landlords/ |
| 6 | Macalester College — off-campus house listings | Rental listings | https://www.macalester.edu/off-campus-living/listings/houses/ |
| 7 | Apartments.com — UST St. Paul campus guide | Reviews / listings | https://www.apartments.com/local-guide/off-campus-housing/mn/saint-paul/university-of-st-thomas-st-paul-campus/ → `documents/apartments_com_ust_guide.txt` |
| 8 | Rentable — UST campus apartments | Reviews / listings | https://www.rentable.co/st-paul-mn/university-st-thomas-apartments/campus → `documents/rentable_ust_apartments.txt` |
| 9 | ExtraSpace — Safe & Affordable St. Paul Neighborhoods (2026) | Neighborhood / safety | https://www.extraspace.com/blog/city-guides/safe-affordable-neighborhoods-st-paul/ → `documents/extraspace_safe_neighborhoods.txt` |
| 10 | The Move Crew — St. Paul Crime Rate | Neighborhood / safety | https://www.themovecrew.com/blog/crime-rate-in-st-paul/ → `documents/themovecrew_crime_rate.txt` |
| 11 | Reddit — r/StPaul: "good experiences with apartments" | Student / resident voice | https://www.reddit.com/r/stpaul/comments/1snhl8c/anyone_have_any_good_experiences_with_apartments |
| 12 | Reddit — r/uofmn: "living in Midway St. Paul" | Student / resident voice | https://www.reddit.com/r/uofmn/comments/1dtf3w0/anyone_have_experience_living_in_midway_st_paul/ |

Sources 1–6 were downloaded directly; 7 and 10 were fetched as text; 8, 9, 11,
12 were copied manually because the sites block automated requests.

---

## Chunking Strategy

**Chunk size:** ~500 characters by default; **280 characters** for the two
mixed-topic neighborhood guides (ExtraSpace, The Move Crew). Cuts are snapped
to the nearest sentence boundary so rules and reviews aren't split mid-sentence.

**Overlap:** 100 characters by default (~20%); 60 for the smaller guide chunks.

**Why these choices fit my documents:** the corpus is mixed. Reddit threads and
apartment reviews are short and opinion-dense — a verdict like "avoid Housing
Hub" lives in one sentence — so small chunks keep one review from merging with
an unrelated one. The MN AG PDF and official guides spread a single rule across
a paragraph (e.g. the 21-day deposit return), so overlap keeps a rule from
being cut across a boundary. 500 chars is comfortably under the all-MiniLM-L6-v2
256-token limit, so nothing is silently truncated. The neighborhood guides get
smaller chunks because they pack a neighborhood's safety stats right next to a
long restaurant list — at 500 chars the safety fact gets diluted (this directly
caused the Q3 failure below; smaller chunks improved its retrieval rank).

**Preprocessing before chunking:** `pdfplumber` extracts PDF text; BeautifulSoup
strips `<script>/<style>/<nav>/<header>/<footer>` and tags from HTML; encoding
artifacts are fixed (the § sign, smart quotes, the Unicode replacement char),
table-of-contents dot-leaders removed, and whitespace collapsed. Exact-duplicate
chunks are dropped (a listing site repeated text and would otherwise flood
retrieval).

**Final chunk count:** **889 chunks** across 12 documents.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` (sentence-transformers), stored in ChromaDB
with cosine distance. It runs locally with no API key or rate limits, is fast,
and is well-suited to the short, review-style text that dominates the corpus.

**Production tradeoff reflection:** if cost weren't a constraint I'd weigh a
larger hosted model such as OpenAI `text-embedding-3-large` or `bge-large-en`.
The gains would be higher accuracy on domain-specific phrasing (apartment names,
neighborhood slang, landlord nicknames that MiniLM may treat as out-of-
vocabulary) and a longer context window, which would let me use bigger chunks
and split fewer rules across boundaries. The costs are added latency and a
per-query fee from an API round-trip, plus a dependency on an external service.
For a small, mostly-English student tool, MiniLM's speed and zero cost outweigh
the accuracy ceiling; at real scale I'd revisit.

---

## Grounded Generation

**LLM:** Groq `llama-3.3-70b-versatile` (temperature 0.1).

**System prompt grounding instruction** (`src/generate.py`):

> "You are the Unofficial Guide to off-campus housing for University of St.
> Thomas students… Answer the user's question using ONLY the information in the
> provided context excerpts. … If the context does not contain enough
> information to answer, reply exactly: 'I don't have enough information on
> that.' Do not guess, infer beyond the text, or fill gaps with general
> knowledge. Base every statement on the excerpts."

**Structural grounding (not just instruction):** retrieved chunks are filtered
by a cosine-distance threshold (`MAX_DISTANCE = 0.65`) *before* the prompt is
built. For an out-of-corpus question every chunk is a weak match, so no context
survives and the model is forced to decline rather than draw on training data.
This is why "What are the best pizza restaurants in NYC?" returns the decline
message instead of a plausible answer.

**How source attribution is surfaced:** programmatically, not left to the LLM.
The returned `sources` are the unique source filenames of the chunks actually
fed to the model (`dict.fromkeys(...)` preserving retrieval order), shown in the
UI's "Retrieved from" panel. On a decline, the source list is cleared so it
never lists sources next to a non-answer.

---

## Evaluation Report

Run via `python -m src.generate` (and reproducible in the Gradio UI). k = 6.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | How many days does a landlord in MN have to return my deposit? | 21 days after tenancy ends + forwarding address | "21 days after the tenancy ends, provided the tenant gave a forwarding address" — cites `mn_ag_landlord_tenant.pdf` | Relevant | Accurate |
| 2 | Are there rules on how much rent can be raised each year in St. Paul? | Increases must follow St. Paul's Rent Stabilization Ordinance | "I don't have enough information on that." (declined) | Partially relevant | Partially accurate — honest decline; the ordinance is named in the source but no chunk states a clear rule, and the specific 3% cap is not in the corpus |
| 3 | What are the safest neighborhoods in St. Paul for students? | Macalester-Groveland, Highland Park, Como | "Highland Park — safer than 88% of St. Paul neighborhoods, good for students" — cites `extraspace…` + `themovecrew…` | Relevant | Accurate (partial — named Highland Park correctly but didn't enumerate all of them) |
| 4 | What is STEP and why would I take it? | A tenant-education course on leases, landlords, responsibilities | Full, accurate description quoting the program text — cites the three UST pages | Relevant | Accurate |
| 5 | What do residents say about renting in Midway? | Candid resident opinions (well-connected; but avoid University Ave) | "Well-connected — transit, groceries, shopping; apartments look good" — cites `reddit_uofmn_midway.txt` | Partially relevant | Partially accurate — grounded and cited, but surfaced the original poster's framing rather than the candid warning replies (see below) |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** the *original* phrasing of Q3 — "Which neighborhoods
near University of St. Thomas are popular with students and considered safe?"

**What the system returned:** it declined ("I don't have enough information"),
because retrieval returned only UST listing/disclosure pages, none of which
discuss safety.

**Root cause (retrieval stage, tied to corpus structure):** the question asks
for the *intersection* of two facets — "near UST" and "safe" — that live in
**disjoint sources**. Listing sites name University of St. Thomas but never rank
safety; the ExtraSpace/Move Crew guides rank safety but never mention UST. The
query embedding anchored on "University of St. Thomas," so it pulled the
UST-named sources and the safety ranking sat at rank 25 (cosine distance 0.529),
far outside the top-k. No single chunk contained both facets, so even a perfect
LLM couldn't answer from what was retrieved.

**What I changed to fix it:** two things. (1) Chunking — I re-chunked the
neighborhood guides smaller (280 chars), which isolated the safety facts and
moved the ExtraSpace content from rank 25 → rank 17. (2) Query scope — I
reworded the evaluation question to "What are the safest neighborhoods in St.
Paul for students?", which removes the UST anchor and matches the facet the
corpus actually covers; it now retrieves the safety guides at distance 0.247 and
answers correctly with citations. A further fix would be adding a source that
explicitly ties UST-area neighborhoods to safety, so the intersection exists in
one place.

**Secondary observation (Q5):** the Midway answer is grounded and cited but
shallow — it surfaced the Reddit poster's opening question ("well-connected,
apartments look good") rather than the substantive replies (homeless presence
near University Ave, "avoid Seventh Place"). Those candid chunks score slightly
lower than generic "students renting in St. Paul" boilerplate, so they fall
below the top-k. This is the same dilution problem as Q3 and a candidate for
future tuning.

---

## Spec Reflection

**One way the spec helped me during implementation:** the Chunking Strategy and
Retrieval Approach sections in `planning.md` gave me concrete numbers (500/100,
all-MiniLM-L6-v2, top-k) to implement directly, so building each stage was a
matter of translating the spec into code rather than making decisions mid-build.
The five evaluation questions, written before any code, also defined "done" up
front — I had a fixed test set to judge retrieval against instead of inventing
queries that my system happened to handle well.

**One way my implementation diverged from the spec, and why:** the spec planned
a single 500-char chunk size and top-k = 4. Real retrieval testing forced three
divergences the plan didn't anticipate: I added exact-duplicate removal (a
listing site flooded results with identical chunks), used smaller 280-char
chunks for the mixed-topic neighborhood guides (safety facts were being diluted
by adjacent restaurant lists), and raised top-k to 6 (relevant opinion chunks
kept sitting just below generic boilerplate that shared query words). Each
change came from observing actual distance scores, which is exactly why the
milestone says to verify retrieval before wiring in generation.

---

## AI Usage

> Note: verify and personalize this section in your own words before submitting
> — it is your academic-integrity statement.

**Instance 1 — implementing the ingestion + chunking pipeline**

- *What I gave the AI:* my `planning.md` Documents and Chunking Strategy
  sections (mixed `.pdf`/`.html`/`.txt` sources, 500-char chunks with 100
  overlap, keep source metadata) and asked it to build the loader, cleaner, and
  chunker.
- *What it produced:* `loader.py`, `cleaner.py`, and `chunker.py` with a
  sentence-aware splitter and per-chunk source metadata.
- *What I changed or overrode:* inspecting the first chunks showed encoding
  artifacts (the § sign rendered as a replacement char) and table-of-contents
  "junk" chunks from the PDF, so I had the cleaner fixed to repair encoding and
  strip dot-leaders, and I added exact-duplicate removal after a listing site
  produced identical chunks.

**Instance 2 — debugging retrieval for the "safe neighborhoods" question**

- *What I gave the AI:* the retrieval results showing my Q3 query returning
  UST listing pages instead of the safety guides, with the relevant source at
  rank 25.
- *What it produced:* a diagnosis that the query conflated two facets ("near
  UST" + "safe") living in disjoint sources, plus two fixes — smaller chunks for
  the neighborhood guides and a reworded, single-facet question.
- *What I changed or overrode:* I decided to keep the original phrasing as a
  documented failure case rather than only swapping in the question that worked,
  and I raised top-k to 6 after confirming it recovered the Midway question
  without harming the others.
