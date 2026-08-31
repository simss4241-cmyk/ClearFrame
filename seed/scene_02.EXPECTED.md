# scene_02 — expected findings

Test fixture for `seed/scene_02.txt`. Deliberately shares **no literal strings** with `scene_01.txt`, so anything the extractor finds here it found by reasoning, not by matching.

Every brand, person, and photographer in the scene is invented. The composition, the woodblock print, and the poem are real and genuinely public domain.

## What should be extracted

| # | Department | Element | Expected | Rule | Why |
|---|---|---|---|---|---|
| 1 | SOUND_MUSIC | *Rhapsody in Blue* (1924) in a 1959 Columbia master | **AMBER** | MUS-002 | Composition entered US public domain 1 Jan 2020; the 1959 recording is a separate, protected work. The classic trap. |
| 2 | CAMERA_VISUALS | Hokusai, *The Great Wave off Kanagawa*, 1831 | **GREEN** | VIS-002 | Author died 1849. Unambiguously public domain. |
| 3 | CAMERA_VISUALS | Photograph credited "R. Delacroix-Hale, 1978" | **AMBER** | DEFAULT-000 | Invented photographer — unresearchable by design. Should land as `AMBER / UNRESOLVED`, not a guess. This is the honesty test. |
| 4 | CAMERA_VISUALS | 1962 Coast Guard newsreel footage | **AMBER** | ARCH-001 | Archival broadcast footage: network licensor plus talent/union re-use obligations. |
| 5 | CAST_CHARACTERS | Dr. Helena Voss, marine archaeologist, Savannah | **AMBER** | DEFAULT-000 | Invented character. Does not match living person; correctly lands on DEFAULT-000. |
| 6 | LOCATIONS_SETS | 1147 Beaumont Street, Savannah, GA | research-dependent | LOC-001 | Real private commercial/residential street address. Location release required. |
| 7 | PROPS_BRANDS | Kestrel Tonic — "tastes like the inside of a pond," recalled in four states | **AMBER** | PRP-002 | Invented brand, disparaging depiction. Unregistered common-law rights cannot be ruled out. |
| 8 | SCRIPT_SIGNAGE | Phone `555-0142` | **GREEN** | SIG-002 | Inside the reserved NANPA fictitious range. |
| 9 | SCRIPT_SIGNAGE | Phone `912-447-3318` | **RED** | SIG-001 | Outside the 555 range. |
| 10 | SCRIPT_SIGNAGE | Georgia plate `4TH-9920` | **AMBER** | SIG-004 | On-screen vehicle registration. Prop format verification required. |
| 11 | SCRIPT_SIGNAGE | `kestreltonic.com` | **AMBER** | SIG-003 | On-screen web domain name. Studio ownership or clearance verification required. |
| 12 | CAMERA_VISUALS | Dickinson, "Because I could not stop for Death" | **GREEN** | LIT-002 | Died 1886, poem published 1890. Public domain literary quote. |

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
