# CLEARFRAME

**A screenplay clearance agent.** Screenplay in — cited, risk-rated clearance report out. Then the flagged items stay under watch.

Built for [Agentic Cinema: The Blockbuster Hackathon](https://agentic-cinema.devpost.com/) · **Parallel track** · Google Cloud + Gemini.

---

## The problem

Before a film can shoot — and before an insurer will issue the Errors & Omissions policy a distributor requires — the screenplay has to pass **script clearance**. A human analyst reads it line by line and flags everything that could draw a claim: a song cue, a brand on a coffee cup, a painting on a wall, a character who shares a name with a real person in the same city and profession, a street address that actually exists, a phone number outside the reserved 555 range.

Then they research each one. Who owns it, is it still in copyright, is it in litigation, what does it cost to use. The output is a report: every element, its rights status, its risk rating, and the source that justifies the rating.

It takes days to weeks. It costs thousands. It's redone after every rewrite. And it goes stale immediately — rights get sold, suits get filed, and works enter the public domain every January 1st.

## What CLEARFRAME does

1. **Ingest** a screenplay and parse it into structured scenes
2. **Extract** every clearable element across nine industry categories
3. **Research** each one against the live web via Parallel, keeping citations attached
4. **Score** RED / AMBER / GREEN with a deterministic rule engine
5. **Report** with rights holder, basis, citations, and confidence per item
6. **Watch** the flagged items with Parallel Monitor, so the report re-flags itself when the world changes

Step 6 is the point. Clearance isn't a document, it's a standing obligation.

## How it's built

**A language model never assigns a risk rating.** Gemini researches and summarizes; a plain Python rule engine reads the facts and decides the rating. Every verdict carries the ID of the rule that produced it. Reproducible, auditable, and deterministic by construction.

**Every fact carries its source.** Parallel returns a `basis` — citations, reasoning, and a confidence level per claim. That maps almost exactly onto what a clearance report legally has to contain, and it's threaded through to the UI unmodified. A finding without a citation is treated as a bug.

**Unknown is a valid answer.** Unresolvable elements come back `AMBER / UNRESOLVED`. In a legal workflow, an admitted gap beats a confident guess.

### Stack

| Layer | Technology |
|---|---|
| Agent orchestration | `google-adk` — Sequential and Parallel agent topology |
| Reasoning | Gemini via `google-genai`, structured output throughout |
| Web research | Parallel **Search**, **Task**, and **Monitor** APIs via `parallel-web` |
| Storage | Firestore · Cloud Storage |
| Host | Cloud Run |
| Frontend | Static HTML/CSS/JS, no build step |

### Architecture

```
screenplay → Intake → Extraction → ResearchFanout ─┬─ Music     ┐
                                                    ├─ Brand     │ each a
                                                    ├─ Person    │ Parallel
                                                    ├─ Location  │ Search/Task
                                                    └─ ...       ┘ call
                                                          │
                                    Risk Engine (plain Python, no model)
                                                          │
                                              Report ──► Frontend
                                                          │
                            Parallel Monitor ◄── watch RED/AMBER items
                                    │
                            webhook → re-score → new verdict, history preserved
```

See [`docs/SPEC.md`](docs/SPEC.md) for the full design.

## Running it

Setup instructions are in [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

```bash
cp .env.example .env        # fill in GOOGLE_CLOUD_PROJECT and PARALLEL_API_KEY
pip install -r backend/requirements.txt
uvicorn backend.api.main:app --reload --port 8080
```

## Demo material

`seed/` contains an original screenplay scene written specifically for this project and deliberately loaded with clearance landmines — a public-domain composition in a modern recording, an on-screen address, a non-555 phone number, an unflattering brand depiction. Every brand and person in it is invented. A project about rights clearance shouldn't have a clearance problem of its own.

## License

Apache-2.0. See [LICENSE](LICENSE).
