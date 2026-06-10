# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? --> Off-campus housing for University of St. Thomas students (St. Paul, MN). This is valuable becuase as a student finding a apartment can be stressful and time consuming. An AI tool that can help find information and make descions will make the apartment search much easier. They can be hard to find through official channels because of limited search options and limited information about an area or apratment and what can be don their legally if you have legal questions pertaining to housing.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | UST Off-Campus Housing Search (listing DB) | Official portal of vetted house/apt/duplex listings near campus, with distance-to-campus map | https://offcampushousing.stthomas.edu/housing |
| 2 | UST Housing Resources | University guide: how to search, what to watch for when renting off-campus | https://www.stthomas.edu/student-life/off-campus/housing-resources/ |
| 3 | UST Programs & Services (STEP) | Student Tenant Education Program — leases, negotiating with landlords, landlord incentives | https://www.stthomas.edu/student-life/off-campus/programs-services/ |
| 4 | UST Disclosures for Renters & Landlords | Required disclosures and tenant/landlord obligations | https://www.stthomas.edu/student-life/off-campus/housing-resources/disclosures-renters-landlords/ |
| 5 | UST listings — Macalester-Groveland | Prices/amenities in the closest student neighborhood | https://offcampushousing.stthomas.edu/housing/neighborhood-Macalester+Groveland |
| 6 | Macalester College off-campus houses | Same neighborhood, different listing pool (house rentals) | https://www.macalester.edu/off-campus-living/listings/houses/ |
| 7 | MN Attorney General — Landlords & Tenants: Rights & Responsibilities (PDF) | Authoritative MN tenant law: deposits, repairs, eviction | https://www.ag.state.mn.us/brochures/publandlordtenants.pdf |
| 8 | City of St. Paul — Tenant Protections | St. Paul-specific rules: 3% rent cap, security-deposit limits, application fees | https://www.stpaul.gov/departments/safety-inspections/rent-buy-sell-property/renting-property/tenant-protections |
| 9 | Apartments.com — UST St. Paul campus guide | Aggregated complexes, prices, and ratings near campus | https://www.apartments.com/local-guide/off-campus-housing/mn/saint-paul/university-of-st-thomas-st-paul-campus/ |
| 10 | Rentable — UST campus apartments | Resident reviews and rent data by complex | https://www.rentable.co/st-paul-mn/university-st-thomas-apartments/campus |
| 11 | ExtraSpace — Safe & affordable St. Paul neighborhoods (2026) | Mac-Groveland, Highland Park, Como compared on safety and cost | https://www.extraspace.com/blog/city-guides/safe-affordable-neighborhoods-st-paul/ |
| 12 | The Move Crew — St. Paul crime rate & map | Crime stats by area for renter safety context | https://www.themovecrew.com/blog/crime-rate-in-st-paul/ |
| 13 | Reddit — r/StPaul: "Anyone have any good experiences with apartments" | Resident opinions on which St. Paul apartments/landlords are actually good | https://www.reddit.com/r/stpaul/comments/1snhl8c/anyone_have_any_good_experiences_with_apartments |
| 14 | Reddit — r/uofmn: "Anyone have experience living in Midway St. Paul" | Student perspectives on the Midway neighborhood (between St. Paul campuses) | https://www.reddit.com/r/uofmn/comments/1dtf3w0/anyone_have_experience_living_in_midway_st_paul/ |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** ~500 characters (roughly 100–120 tokens), split on sentence/paragraph boundaries where possible.

**Overlap:** 100 characters (~20%).

**Reasoning:** My corpus is mixed. Reddit threads and apartment reviews (sources 9–14) are short and opinion-dense — a key fact like "this landlord kept my deposit" often lives in a single sentence, so chunks must stay small enough that one review's verdict doesn't merge with an unrelated one. The official guides and the MN Attorney General PDF (sources 2–4, 7) are long and spread a single fact across a paragraph (e.g. the 21-day deposit-return rule), so I keep 100 characters of overlap so a rule isn't cut across a chunk boundary. 500 characters is also comfortably under the all-MiniLM-L6-v2 256-token limit, so no chunk gets silently truncated during embedding.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** `all-MiniLM-L6-v2` via sentence-transformers — small, fast, runs locally with no API cost, and well-suited to short review-style text.

**Top-k:** 4 chunks per query.

**Production tradeoff reflection:** If cost weren't a constraint, I'd weigh a larger hosted model such as OpenAI `text-embedding-3-large` or `bge-large-en`. The main gains would be higher accuracy on domain-specific phrasing (apartment names, neighborhood slang, landlord nicknames that MiniLM may treat as out-of-vocabulary) and a longer context window, which would let me use bigger chunks and split fewer rules across boundaries. The tradeoffs are added latency and per-query cost from an API round-trip, plus a dependency on an external service being available — versus MiniLM running locally and instantly. For a small student-facing tool where the text is mostly short and English, MiniLM's speed and zero cost outweigh the accuracy ceiling; at real scale I'd revisit.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | How many days does a landlord in Minnesota have to return my security deposit after I move out? | 21 days after the tenancy ends and the tenant gives a forwarding address; otherwise the tenant may sue (MN AG guide, source 7). |
| 2 | Is there a cap on how much my rent can be raised each year in St. Paul? | Yes — St. Paul's rent stabilization ordinance caps annual rent increases at 3% (City of St. Paul Tenant Protections, source 8). |
| 3 | Which neighborhoods near University of St. Thomas are popular with students and considered safe? | Macalester-Groveland, Highland Park, and Union Park — close to campus, walkable, and among St. Paul's safer areas (sources 5, 11, 12). |
| 4 | What is the Student Tenant Education Program (STEP) and why would I take it? | A self-paced Canvas course on leases, landlord relationships, and responsible renting; some landlords offer incentives to students who complete it (source 3). |
| 5 | What do students/residents say about renting in the Midway area of St. Paul? | Mixed first-hand experiences from residents — pulled from the r/uofmn Midway thread (source 14); answer should reflect the actual posted opinions, not a generic description. |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. **Stale or conflicting facts across sources.** Rent figures, the 3% cap, and listing prices change over time, and a Reddit comment from 2024 may contradict the current city ordinance. If retrieval mixes an outdated chunk with a current one, the model could state a wrong number confidently. Mitigation: keep the source URL/date in each chunk's metadata and surface it in the answer so users can judge recency.

2. **Key rules split across chunk boundaries.** A single legal rule (e.g. "21 days... or the tenant may sue for double the deposit") can land half in one chunk and half in the next. If retrieval returns only the first half, the model has incomplete context and may give a partial answer. Mitigation: the 100-character overlap, plus reviewing the MN AG PDF chunks specifically since it's the longest, most rule-dense document.

3. **Off-topic retrieval from generic listing pages.** Sources like Apartments.com and Rentable contain lots of boilerplate (amenities lists, SEO text) that can crowd out the substantive review content during embedding, pulling irrelevant chunks for opinion-style questions. Mitigation: strip boilerplate during preprocessing and lean on the higher-signal Reddit/review sources for opinion queries.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

```
┌──────────────────┐   ┌──────────────┐   ┌────────────────────────┐   ┌───────────────┐   ┌────────────────┐
│ 1. Ingestion     │   │ 2. Chunking  │   │ 3. Embedding + Store   │   │ 4. Retrieval  │   │ 5. Generation  │
│                  │──▶│              │──▶│                        │──▶│               │──▶│                │
│ Load documents/  │   │ 500-char     │   │ all-MiniLM-L6-v2       │   │ Embed query,  │   │ Groq LLM +     │
│ (.txt/.md/.pdf), │   │ chunks, 100  │   │ (sentence-transformers)│   │ top-k=4 from  │   │ grounding      │
│ strip boilerplate│   │ overlap,     │   │ → vectors stored in    │   │ ChromaDB by   │   │ prompt; cite   │
│ keep src + URL   │   │ keep metadata│   │ ChromaDB w/ metadata   │   │ cosine sim    │   │ source URLs    │
└──────────────────┘   └──────────────┘   └────────────────────────┘   └───────────────┘   └────────────────┘
   pdfplumber (PDFs)      Python                                                              Gradio/Streamlit UI
```

**Stage tools:** ingestion = Python + `pdfplumber` (for the MN AG PDF) · chunking = custom `chunk_text()` · embedding/store = `sentence-transformers` + `chromadb` · retrieval = ChromaDB similarity query · generation = `groq` SDK, with a Gradio or Streamlit query interface (Milestone 5).

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:** I'll use Claude. Input: my Documents table and Chunking Strategy section (500-char chunks, 100 overlap, keep source URL in metadata) plus the note that I have mixed `.txt`/`.md`/`.pdf` files. Expected output: a loader that reads `documents/`, strips boilerplate, and a `chunk_text()` function matching my sizes that attaches source metadata to each chunk. I'll verify by checking the chunk count is reasonable and spot-checking that no rule from the MN AG PDF is cut mid-sentence.

**Milestone 4 — Embedding and retrieval:** I'll use Claude. Input: my Retrieval Approach section (all-MiniLM-L6-v2, top-k=4, ChromaDB). Expected output: code that embeds all chunks, persists them to a ChromaDB collection with metadata, and a `retrieve(query)` that returns the top-4 chunks with their source URLs. I'll verify by running my 5 evaluation questions and checking the retrieved chunks actually contain the expected answer.

**Milestone 5 — Generation and interface:** I'll use Claude. Input: my Grounded Generation goals (answer only from retrieved chunks, cite sources) and a choice of Gradio. Expected output: a function that builds a grounded prompt from the top-k chunks, calls the Groq LLM, and a simple UI. I'll verify by asking a question with no answer in the corpus and confirming the system says it doesn't know rather than hallucinating.
