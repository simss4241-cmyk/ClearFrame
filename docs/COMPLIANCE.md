# Compliance checklist

Every item traces to the [Official Rules](https://agentic-cinema.devpost.com/rules). Stage One judging is **pass/fail** on these and *"may be conducted with the assistance of automated tools"* — so a missing license file or an unreachable URL kills the entry before a human ever sees the work.

Re-run this list before submitting.

## Deadlines

| Date | What |
|---|---|
| **31 Aug 2026, 11:59pm PST** | Last day to request the $100 Google Cloud credit ([form](https://forms.gle/XPe837tzogh8L5sX6)). Credit takes 1–5 business days to approve — request it early, it is not guaranteed. |
| **7 Sep 2026, 2:00pm PDT** | Submission deadline. Hard. Late entries are disqualified. |
| 23 Sep – 7 Oct 2026 | Judging period |

## Eligibility gates

- [ ] Entrant is above the age of majority in their jurisdiction
- [ ] Entrant is not resident in an excluded country/territory
- [ ] Registered on Devpost and joined this hackathon
- [ ] Team is ≤ 4 people, all added as members on the Devpost project

## The two clauses most likely to disqualify us

**New work only.** *"Projects must be newly created by the entrant during the Contest Period. The Project must be Your original creation not a modification or extension of Your or anyone else's existing work."* Contest period opened 27 July 2026.

- [ ] Repo initialized fresh; **no commit predates 27 July 2026**
- [ ] No code carried over from any pre-existing codebase
- [ ] README does not describe the project as a fork, port, or continuation of anything

**Google-only AI.** *"Projects may only use Google Cloud artificial intelligence tools... No other AI models, agent frameworks, or AI APIs are permitted, regardless of vendor — this includes but is not limited to AWS, Microsoft, OpenAI, and Anthropic AI tools."*

- [ ] `requirements.txt` audited — no OpenAI, Anthropic, Cohere, Mistral, HuggingFace inference, Ollama, local model runtimes
- [ ] No third-party agent framework (LangChain-as-orchestrator, LlamaIndex, CrewAI, AutoGen). ADK is the orchestrator.
- [ ] No ComfyUI, no Stable Diffusion, no non-Google image or video generation
- [ ] Any AI-assisted development was done with Gemini, not a competitor's model

*Note: this clause is written about the Project. The IBM and Replit tracks explicitly police development tooling too, which signals sponsors do look at how submissions were built — so keep the build story clean and Gemini-centric.*

## Runtime integration — must be visible in code, not just the README

**Google Cloud.** Accepted packages: `google-adk`, `google-genai`, `google-generativeai`, `google-cloud-aiplatform` (any generation).

- [ ] At least one accepted package imported and **called on the live request path**
- [ ] Reachable from an app or backend entry point, not an unused helper

**Parallel.** *"your project must actively use Parallel's Search API at runtime — for example, via the official parallel-web SDK."*

- [ ] `parallel-web` imported in `backend/tools/parallel_tools.py`
- [ ] **Search API** specifically is called — this is the named requirement. Task and Monitor are additive, not substitutes.
- [ ] Calls happen during a real user request, provable in the demo video

## Submission package

- [ ] **Hosted project URL** — live and publicly reachable, no login wall. Test it from a logged-out browser on another network.
- [ ] **Public repo** on GitHub, GitLab, or Bitbucket
- [ ] **LICENSE file at repo root**, OSI-approved, permitting commercial use. Apache-2.0. Must be **detectable in the GitHub About sidebar** — verify it actually renders there, this is the specific thing the rules call out.
- [ ] Repo contains all source, assets, and instructions needed to run it
- [ ] **Demo video** — ≤ 3 minutes, public on YouTube or Vimeo, English or English-subtitled, shows the project *actually functioning*
- [ ] Text description: features, technologies, data sources, findings and learnings
- [ ] **Partner track selected: Parallel**
- [ ] Devpost submission form complete

## Demo video constraints

The video rules are unusually strict and are a real disqualification path.

- [ ] Under 3:00 — anything past that is not evaluated
- [ ] Original, unpublished work
- [ ] **No third-party advertising, slogans, logos, or trademarks** that imply sponsorship. Careful: our demo screenplay deliberately contains brand references. Keep on-screen brand names to invented ones in the seed scene, and don't score the video with licensed music.
- [ ] Nothing that infringes a third party's publicity, privacy, or IP rights
- [ ] Shows the platform it was built for (web) actually running

*The irony is worth stating out loud: a project about rights clearance cannot itself have a clearance problem. Use invented brands and invented people in the seed scene, and public-domain or original music in the video.*

## Judging criteria — equally weighted

Design and Quality of Idea together are half the score, and are where most entries are weakest.

| Criterion | How CLEARFRAME answers it |
|---|---|
| **Technological Implementation** | Multi-agent ADK topology, deterministic rule engine separate from the models, Parallel's `basis` threaded end to end |
| **Design** | A complete product — script view with inline risk highlighting, live report, verdict history — not a CLI demo |
| **Potential Impact** | A real, costly, repeated bottleneck with a named buyer; E&O insurance makes it non-optional |
| **Quality of the Idea** | Non-obvious use of Parallel: provenance and change-detection, not search-as-a-box |

## Pre-submit smoke test

- [ ] Clone the public repo to a clean machine, follow the README, and get it running
- [ ] Open the hosted URL logged out, from a different network
- [ ] Confirm the video is public, not unlisted-only-by-accident, and plays without login
- [ ] Confirm the license shows in the GitHub About sidebar
- [ ] Confirm no secrets in git history — check the whole history, not just HEAD
