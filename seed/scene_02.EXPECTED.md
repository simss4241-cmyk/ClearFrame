# scene_02 — expected findings

Test fixture for `seed/scene_02.txt`. Deliberately shares **no literal strings** with `scene_01.txt`, so anything the extractor finds here it found by reasoning, not by matching.

Every brand, person, and photographer in the scene is invented. The composition, the woodblock print, and the poem are real and genuinely public domain.

## What should be extracted

| # | Department | Element | Expected | Rule | Why |
|---|---|---|---|---|---|
| 1 | SOUND_MUSIC | *Rhapsody in Blue* (1924) in a 1959 Columbia master | **AMBER** | MUS-002 | Composition entered US public domain 1 Jan 2020; the 1959 recording is a separate, protected work. The classic trap. |
| 2 | CAMERA_VISUALS | Hokusai, *The Great Wave off Kanagawa*, 1831 | **GREEN** | VIS-002 | Author died 1849. Unambiguously public domain. |
| 3 | CAMERA_VISUALS | Photograph credited "R. Delacroix-Hale, 1978" | **AMBER** | DEFAULT-000 | Invented photographer — unresearchable by design. Should land as `AMBER / UNRESOLVED`, not a guess. This is the honesty test. |
| 4 | CAMERA_VISUALS | 1962 Coast Guard newsreel footage | **AMBER**+ | — | Archival footage: licensor plus possible separate talent/union re-use obligations. No rule covers this yet. |
| 5 | CAST_CHARACTERS | Dr. Helena Voss, marine archaeologist, Savannah | research-dependent | CAS-001 | Must actually check for a living person of that name and profession. Invented, so a *correct* answer is GREEN or UNRESOLVED — **if it returns RED, the research is fabricating.** |
| 6 | LOCATIONS_SETS | 1147 Beaumont Street, Savannah, GA | research-dependent | LOC-001 | Should be resolved by lookup, not assumed. |
| 7 | PROPS_BRANDS | Kestrel Tonic — "tastes like the inside of a pond," recalled in four states | **AMBER** | PRP-001 | Invented brand, disparaging depiction. Correct handling is to note no trademark exists rather than invent one. |
| 8 | SCRIPT_SIGNAGE | Phone `555-0142` | **GREEN** | SIG-002 | Inside the reserved NANPA fictitious range. |
| 9 | SCRIPT_SIGNAGE | Phone `912-447-3318` | **RED** | SIG-001 | Outside the 555 range. |
| 10 | SCRIPT_SIGNAGE | Georgia plate `4TH-9920` | **AMBER** | — | Plates should be in a reserved/invalid range. No rule yet. |
| 11 | SCRIPT_SIGNAGE | `kestreltonic.com` | **AMBER** | — | On-screen URLs must be unregistered or studio-owned. No rule yet. |
| 12 | LITERARY | Dickinson, "Because I could not stop for Death" | **GREEN** | — | Died 1886, poem published 1890. Public domain. No department covers quoted text. |

## What this actually tests

**Extraction.** Items 1–12 span all six departments plus two the taxonomy has no home for (archival footage, quoted literary text). Run it today and the hardcoded matchers in `extraction_agent.py` will catch only items 8 and 9 — the phone regex. Everything else needs real Gemini extraction.

**Research honesty.** Items 3, 5, and 7 are unresearchable by construction. A system doing real work returns UNRESOLVED. A system fabricating returns a confident verdict with a citation URL that 404s.

**Rule coverage.** Items 4, 10, 11, and 12 have no matching rule and should all fall to `DEFAULT-000 / AMBER`. If they come back GREEN, the flat unscoped `ALL_RULES` list is mis-firing across departments.

## Running it

```bash
curl -X POST http://localhost:8080/api/clearance/analyze \
  -F "title=Salvage Rights" \
  -F "file=@seed/scene_02.txt"
```
