# Brief 01 — Make it real

**Read `GEMINI.md` first, especially "Prohibited patterns" and "Verification". Every item there came from auditing the current state of this codebase.**

## Situation

The pipeline runs end to end and produces a clearance report. None of it is real.

- `genai.Client()` has never successfully initialized. Gemini has executed **zero** times.
- Parallel has never been successfully called. `client.search(query=...)` is not a valid signature; it raises, and the exception is swallowed.
- Every "finding" comes from hardcoded branches in the fallback extractor, keyed to strings in `seed/scene_01.txt`.
- The citation URLs were written by hand. Several point at domains that do not exist.

Uploading `seed/scene_02.txt` — a screenplay containing a Hokusai woodblock print, Gershwin's *Rhapsody in Blue*, and an invented energy drink — returns Edward Hopper's *Nighthawks*, a Chicago address that appears nowhere in the file, and a 97% confidence badge. The Hopper card is triggered by the word `print` in the line describing the Hokusai.

## Goal

Make the pipeline actually call Gemini and Parallel, and make it fail loudly when it cannot.

Scope is the research and extraction path only. Do not touch the frontend, the risk engine, or the data models in this pass — they are structurally sound.

---

## Work, in order

### 1. Fix credentials and fail loud

`backend/api/main.py` does not load `.env`, so the server never sees configuration. Add `load_dotenv()` at import time.

Add a startup check that resolves the Gemini client **once, at boot**, and refuses to start if it cannot. A misconfigured deployment must not boot into a state where it silently serves fiction.

Verify with `python scripts/poke.py check` before continuing.

### 2. Delete the fallback extractor

Remove the entire pattern-based block at the bottom of `backend/agents/extraction_agent.py` — every `if "Veloce" in text`, every hardcoded `Element(...)`. Do not replace it with a better fallback. Delete it.

If the Gemini extraction call fails, raise. The API returns a 502 with the underlying error. That is the correct behavior.

Same treatment for the three `except Exception: pass` blocks in `backend/tools/parallel_tools.py` and `backend/agents/watch_agent.py`.

### 3. Fix the Parallel Search call

Current code:

```python
res = client.search(query=query)          # no such parameter — raises
```

Correct shape:

```python
res = client.search(
    objective="Determine whether the 1924 Gershwin composition Rhapsody in Blue "
              "is in the US public domain, and whether a 1959 Columbia master "
              "recording of it is separately protected.",
    search_queries=["Rhapsody in Blue copyright status",
                    "1959 Columbia Masterworks recording copyright"],
    mode="advanced",
)
```

`objective` is a natural-language goal, not keywords — that distinction drives result quality. `scripts/poke.py search` demonstrates a working call; run it and read the response shape before writing against it.

Build the objective per element from `element.text`, `element.subtype`, `element.department`, and `element.context_snippet`. Nothing about the objective may be specific to a particular seed file.

### 4. Derive facts from responses, not from branches

`deep_research_element_parallel()` currently branches on `Department` and assigns hardcoded `Facts`. Replace with:

1. Call Parallel Search with the constructed objective.
2. Pass the returned excerpts to Gemini with a `response_schema` matching `Facts`, and instruct it to populate **only** fields the excerpts actually support, leaving everything else `None`.
3. Build `BasisItem` entries using URLs copied verbatim from the Parallel response. Never construct a URL.
4. If the excerpts do not support a determination, return empty facts. The risk engine will correctly produce `AMBER / DEFAULT-000`.

Step 4 is the point of the whole exercise. An honest `UNRESOLVED` is a success, not a gap to paper over.

### 5. Fix the Monitor call

```python
client.monitor.create(query=..., cadence="daily")     # wrong
```

Correct:

```python
client.monitor.create(
    type="event_stream",
    frequency="1d",
    processor="lite",
    settings={"query": ...},
    webhook={"url": f"{PUBLIC_BASE_URL}/api/clearance/webhooks/monitor",
             "event_types": ["monitor.event.detected"]},
    metadata={"external_id": element.id},
)
```

Parallel cannot reach `localhost`. When `PUBLIC_BASE_URL` is unset or local, skip webhook registration and log that clearly — do not register a monitor pointing at an unreachable URL.

### 6. Fix the phone regex

`\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b` requires ten digits, so seven-digit numbers like `555-0142` are invisible. This is why no element has ever scored GREEN. Match both seven- and ten-digit forms.

---

## Explicitly out of scope

Do not do these in this pass:

- ADK migration (separate brief)
- Firestore persistence (separate brief)
- Frontend changes of any kind
- New risk rules or new departments
- Anything in `docs/`, `scripts/`, or `seed/`

## Acceptance criteria

The task is complete when **all** of the following hold:

1. `grep -rn "Nighthawks\|Wabash\|Pendelton\|Veloce\|Hopper\|Darktown" backend/` returns nothing.
2. `grep -rn "except Exception:\s*pass" backend/` returns nothing.
3. With credentials unset, `POST /api/clearance/analyze` returns a 5xx with a real error message — **not** a report.
4. With credentials set, `seed/scene_02.txt` produces findings consistent with `seed/scene_02.EXPECTED.md`. Specifically:
   - The Hokusai print is found and no Hopper appears anywhere in the output.
   - `555-0142` is found and rated GREEN.
   - `912-447-3318` is found and rated RED.
   - The invented photographer "R. Delacroix-Hale", the invented character "Dr. Helena Voss", and the invented brand "Kestrel Tonic" all come back `AMBER / DEFAULT-000` or with facts that honestly report no evidence found. **If any of them returns a confident verdict with a citation, the research layer is still fabricating and the task has failed.**
5. Every citation URL in the output resolves to a live page. Open them.
6. `seed/scene_01.txt` still produces a coherent report — findings may differ from before, since they will now be real.

## Note on criterion 4

Three elements in scene_02 are unresearchable by construction. They exist to detect fabrication. A system doing real work returns "no evidence found." A system inventing returns a plausible answer with a citation that 404s.

Returning fewer, honest findings is the successful outcome here. Do not optimize for a full-looking report.
