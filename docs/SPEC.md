# CLEARFRAME — Specification

**Agentic Cinema: The Blockbuster Hackathon · Parallel track**
Target user (per Official Rules §7A): **filmmakers and studio crews** — specifically the production counsel, line producer, and clearance coordinator on an independent feature.

---

## 1. The problem

Before a film can shoot — and before an insurer will issue the Errors & Omissions policy that a distributor requires — the screenplay must pass **script clearance**. A human clearance analyst reads the script line by line and flags every element that could draw a claim: a song cue, a brand on a coffee cup, a painting on a wall, a character who shares a name with a real person in the same city and profession, a street address that actually exists, a phone number that isn't in the 555 range.

For each flagged element they research who owns it, whether it's still in copyright, whether it's in litigation, and what it would cost or risk to use. The output is a **clearance report**: every element, its rights status, its risk rating, and the source that justifies the rating.

This is slow, expensive, and manual. A feature-length script takes days to weeks and costs thousands. It is repeated after every rewrite. And it is *perishable* — rights are sold, lawsuits are filed, and works enter the public domain every January 1st, which means a report is stale the moment it's delivered.

## 2. What CLEARFRAME does

Screenplay in. Cited, risk-rated clearance report out. Then the flagged items stay under watch.

1. **Ingest** — accept a screenplay (PDF, Final Draft `.fdx`, or plain text) and parse it into structured scenes.
2. **Extract** — identify every clearable element and classify it against the industry taxonomy (§4).
3. **Research** — fan out across the elements, grounding each in fresh, cited web evidence via Parallel.
4. **Score** — assign each element a RED / AMBER / GREEN rating using a **deterministic rule engine**, not a model's judgment.
5. **Report** — assemble a clearance report with per-item rights holder, basis, citations, and confidence.
6. **Watch** — register the RED and AMBER items with Parallel Monitor. When the world changes, the report re-flags itself.

Step 6 is what makes this an agent rather than a document generator. Clearance is not a one-time artifact; CLEARFRAME treats the report as a living object with a heartbeat.

## 3. Why Parallel is load-bearing

A clearance report's value is entirely in its *provenance*. "This song is public domain" is worthless; "this song is public domain, per this source, with this reasoning, at this confidence" is the deliverable. Parallel's `basis` field — citations, reasoning, and a confidence level attached to every claim — maps directly onto what the report legally has to contain. We are not using Parallel as a search box; we are using the part of it that produces defensible evidence.

Three Parallel products, each for a distinct reason:

| Product | Used for | Why not something else |
|---|---|---|
| **Search API** | Fast first-pass triage on every extracted element | `turbo` mode, p50 ~200ms, keeps a 100-element script tractable |
| **Task API** | Deep research on elements that survive triage | Returns structured output with `basis` — citations + reasoning + confidence per field |
| **Monitor API** | Standing watch on RED/AMBER items | Push webhooks on change; no cron, no polling, no dedup pipeline to build |

`Extract API` is a stretch goal for pulling full text from a specific rights-holder page or registry record.

## 4. Element taxonomy

Modeled on what a real script clearance report covers. Each extracted element carries a `category`, which selects the research strategy and the scoring rule.

| Category | What we look for | Core clearance question |
|---|---|---|
| `MUSIC` | Song cues, needle drops, score references, lyrics quoted in dialogue | Composition and master rights holders; is the composition in the public domain? |
| `BRAND` | Products, logos, trademarks, corporate names appearing or spoken | Live trademark registration; is the depiction disparaging (which defeats nominative fair use)? |
| `ARTWORK` | Paintings, sculptures, posters, murals, photographs visible in frame | Copyright term of the underlying work; is it PD; who administers it |
| `LITERARY` | Quoted poems, books, articles, speeches, other scripts | Copyright term; PD status; fair-use posture of the quotation length |
| `ARCHIVAL` | Film, TV, news, or documentary footage referenced for insert | Footage licensor; are there separate talent/union re-use obligations |
| `PERSON` | Real named individuals, or characters recognizably based on them | Alive or dead; jurisdiction's right of publicity; defamation exposure |
| `CHARACTER_NAME` | Fictional character names that may collide with real people | Does a real person share this name in the same city and occupation |
| `LOCATION` | Identifiable real businesses, landmarks, addresses | Is the address real; is the business depicted negatively; trademark on trade dress |
| `SIGNAGE` | On-screen text: phone numbers, license plates, URLs, email addresses | Phone in 555 range; plate in reserved range; domain unregistered |

`CHARACTER_NAME` and `SIGNAGE` are the categories that signal genuine domain understanding — they are standard on real clearance reports and would not occur to someone who hadn't looked at one. They are also the two that most obviously need live web data.

## 5. Architecture

```
                         ┌───────────────────────────┐
  screenplay ──────────► │  Cloud Storage (raw)      │
  (pdf/fdx/txt)          └────────────┬──────────────┘
                                      │
  ┌───────────────────────────────────▼──────────────────────────────┐
  │  Cloud Run · ADK service                                          │
  │                                                                   │
  │  SequentialAgent "clearance_pipeline"                             │
  │    1. IntakeAgent      Gemini · structured output → scenes[]      │
  │    2. ExtractionAgent  Gemini · structured output → elements[]    │
  │    3. ResearchFanout   ADK ParallelAgent, one sub-agent per       │
  │       ├─ MusicResearcher      │ category. Each wraps the Parallel │
  │       ├─ BrandResearcher      │ SDK as an ADK FunctionTool with a │
  │       ├─ PersonResearcher     │ category-specific objective and   │
  │       ├─ ...                  │ output schema.                    │
  │    4. RiskEngine       PLAIN PYTHON. No model. See §6.            │
  │    5. ReportAgent      Gemini · assembles narrative + memo        │
  │    6. WatchAgent       registers Parallel Monitors for RED/AMBER  │
  │                                                                   │
  └────────────┬────────────────────────────────┬─────────────────────┘
               │                                │
    ┌──────────▼──────────┐        ┌────────────▼─────────────┐
    │ Firestore           │        │ Parallel Monitor         │
    │ scripts, elements,  │        │ ─ webhook ──────────────►│ /webhooks/monitor
    │ findings, monitors  │        └──────────────────────────┘   re-scores one
    └──────────┬──────────┘                                        element, writes
               │                                                   back to Firestore
    ┌──────────▼──────────────────────────────────────────┐
    │ Frontend (static, Cloud Run)                        │
    │ script left · inline risk highlights · report right │
    └─────────────────────────────────────────────────────┘
```

**Google Cloud at runtime:** Gemini via `google-genai` on Agent Platform, agent orchestration via `google-adk`, Cloud Run, Cloud Storage, Firestore. Optionally Grounding with Parallel Web Search, which is a native Gemini Enterprise Agent Platform integration and the cleanest possible demonstration of Google-plus-Partner working together.

**Parallel at runtime:** `parallel-web` Python SDK, called inside ADK `FunctionTool`s. Imported and invoked in `backend/tools/parallel_tools.py`.

## 6. The deterministic risk engine

The single most defensible technical decision in this project: **a language model never assigns a risk rating.**

Models research and summarize. A plain Python rule engine reads the researched facts and produces the rating. This matters for three reasons — it makes the output reproducible, it makes it auditable (every rating traces to a named rule), and it is exactly the "deterministic, multi-step agent" the sponsors asked for.

Shape of it:

```python
# backend/risk/rules.py
@rule(category="MUSIC", id="MUS-001")
def composition_in_public_domain(el: Element) -> Verdict | None:
    if el.facts.composition_pd is True and el.facts.confidence >= HIGH:
        return Verdict(GREEN, "Composition is in the public domain.", cites=el.facts.cites)
    return None

@rule(category="MUSIC", id="MUS-002")
def master_recording_still_protected(el: Element) -> Verdict | None:
    if el.facts.composition_pd is True and el.facts.master_pd is False:
        return Verdict(AMBER,
            "Composition is PD but this specific recording is not — "
            "license the master or re-record.", cites=el.facts.cites)
    return None

@rule(category="SIGNAGE", id="SIG-001")
def phone_number_outside_555(el: Element) -> Verdict | None:
    if el.subtype == "PHONE" and not is_555(el.text):
        return Verdict(RED, "Phone number is outside the reserved 555 range.",
                       cites=[])   # this rule needs no source; it is arithmetic
```

Rules are ordered; first match wins; every element ends with a rule ID attached. Unmatched elements fall to `AMBER / UNRESOLVED`, which is the honest answer and also the right default for a legal workflow.

`MUS-002` is the kind of rule worth demoing on camera — the composition/master distinction is the classic trap that catches first-time filmmakers who assume "it's old, so it's free."

## 7. Data model

```
Script       id, title, uploaded_at, gcs_uri, page_count, status
Scene        id, script_id, number, heading, page, text
Element      id, script_id, scene_id, category, subtype, text,
             page, line, context_snippet
Finding      id, element_id, facts{}, basis[{url, reasoning, confidence}],
             parallel_search_id, researched_at
Verdict      id, element_id, rating, rule_id, rationale, superseded_by
Monitor      id, element_id, parallel_monitor_id, query, frequency, status
MonitorEvent id, monitor_id, event_group_id, content, cites[], received_at,
             triggered_rescore
```

`Verdict.superseded_by` is what makes the report living: a Monitor event produces a *new* verdict rather than mutating the old one, so the report has a visible history. On screen that reads as "this was GREEN on Aug 14, it's AMBER now, here's the article that changed it."

## 8. Demo material

Do not hunt for a real screenplay — that reintroduces a rights problem into a project about rights, and the irony is not worth the risk. Write one original short scene deliberately loaded with landmines:

- a needle drop of a pre-1928 composition in a modern recording → **AMBER**, MUS-002
- a character named for a real, living, findable person in the same profession → **RED**
- a real street address on screen → **RED**
- a phone number that isn't 555 → **RED**, SIG-001, and instant to explain on camera
- a painting whose author died 80 years ago → **GREEN**
- a brand shown in an unflattering light → **AMBER**

That gives the three-minute video a visible spread of colors and one genuinely surprising finding.

## 9. Build order

1. Repo, license, GCP project, Parallel key, `hello world` that calls Gemini *and* Parallel and prints both. Prove the two dependencies work before building on them.
2. Intake + Extraction on the seeded scene. Structured output only — no free text.
3. One researcher end to end (`MUSIC`), plus rules `MUS-001`/`MUS-002`.
4. Risk engine + report assembly. First screenshot-able artifact.
5. Frontend. Script left, highlights inline, report right.
6. Remaining researcher categories.
7. Monitor + webhook. The second act.
8. Deploy, README, video.

Cut from the bottom if time runs short. Steps 1–5 alone are a complete, coherent submission; 7 is what makes it memorable.

## 10. Open questions

- Confirm exact config for **Grounding with Parallel Web Search** in Gemini Enterprise Agent Platform — decide whether to use it as the primary path or call the `parallel-web` SDK directly. The SDK path is more visible in code, which the rules explicitly reward; grounding is more idiomatic. Likely both: grounding for narrative research, SDK for the structured per-element work.
- `.fdx` parsing is plain XML and easy. PDF screenplay parsing is the risk. Fallback: accept `.fdx` and `.txt` only, and note it as a scoped limitation rather than shipping a flaky PDF path.
- Firestore vs. Postgres on Cloud SQL. Firestore is faster to stand up and free at this scale; nothing in the design needs joins.
