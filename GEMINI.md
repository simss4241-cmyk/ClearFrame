# CLEARFRAME — agent context

Read `docs/SPEC.md` before writing code. Read `docs/COMPLIANCE.md` before adding a dependency.

## What this is

A screenplay clearance agent. Screenplay in, cited and risk-rated clearance report out, flagged items then kept under live watch. Built for the **Agentic Cinema: The Blockbuster Hackathon**, Parallel track. Deadline **7 Sep 2026, 2:00pm PDT**.

Target user, per the Official Rules: filmmakers and studio crews — the production counsel and clearance coordinator on an independent feature.

## Hard constraints — these are eligibility rules, not preferences

**1. Only Google Cloud AI. No exceptions.**
The rules state: *"Projects may only use Google Cloud artificial intelligence tools... No other AI models, agent frameworks, or AI APIs are permitted, regardless of vendor — this includes but is not limited to AWS, Microsoft, OpenAI, and Anthropic AI tools."*

Permitted AI: `google-adk`, `google-genai`, `google-generativeai`, `google-cloud-aiplatform`, plus Parallel's own built-in AI features (Parallel is our track partner).

Banned, and this is a disqualification not a code-review note: OpenAI, Anthropic, LangChain agent abstractions used as an agent framework, LlamaIndex, CrewAI, AutoGen, Ollama, HuggingFace inference, any local model. If a library you are about to install performs inference or orchestrates agents and is not on the permitted list, **stop and ask** rather than installing it.

This restriction is about AI tooling only. Non-AI libraries — web frameworks, parsers, database clients, test runners — are unrestricted.

**2. This must be new work, authored during the contest period.**
The rules require the project be *"newly created by the entrant during the Contest Period"* and *"not a modification or extension of Your or anyone else's existing work."* The contest period began 27 July 2026.

**Do not copy from, import from, or vendor in any pre-existing codebase — including the author's own earlier projects.** Visual design language may be re-created by hand; code may not be carried over. If you find yourself reaching for something that already exists elsewhere on this machine, write it fresh instead.

**3. Parallel must be called at runtime, in code.**
*"Referencing Parallel in your README alone does not satisfy this requirement — the integration must be present in your code."* The `parallel-web` SDK must be imported and invoked on the live request path. Same for Google Cloud.

**4. The repo is public and Apache-2.0.** Never commit a key, a service account JSON, or a `.env`. Check `.gitignore` before every commit.

## Stack

- **Backend** — Python 3.11+, `google-adk` for orchestration, `google-genai` for Gemini, `parallel-web` for Parallel, FastAPI for the HTTP surface.
- **Data** — Firestore. Cloud Storage for uploaded scripts.
- **Frontend** — static HTML/CSS/vanilla JS. No build step, no framework. Dark, cinematic, typographic; the script is the hero of the screen.
- **Host** — Cloud Run, one service, frontend served as static files from it.

## Design rules

**A model never assigns a risk rating.** Models research and summarize; a plain Python rule engine in `backend/risk/` decides RED/AMBER/GREEN. Every verdict carries the ID of the rule that produced it. This is the project's core technical claim — do not dilute it by asking Gemini to "rate the risk."

**Every fact carries its source.** Parallel returns a `basis` with citations, reasoning, and confidence. Thread it through to the UI unmodified. A finding with no citation is a bug, not a finding.

**Structured output everywhere.** Gemini calls use `response_schema`. No parsing free text out of prose.

**Unknown is a valid answer.** An element that can't be resolved is `AMBER / UNRESOLVED`, never a guess. This is a legal workflow; a confident wrong answer is worse than an admitted gap.

## Layout

```
backend/
  agents/      ADK agents — intake, extraction, researchers, report, watch
  tools/       parallel_tools.py — Parallel SDK wrapped as ADK FunctionTools
  risk/        rules.py, engine.py — the deterministic scorer
  models/      pydantic schemas shared by agents and API
  api/         FastAPI routes incl. /webhooks/monitor
frontend/      index.html, app.js, style.css
docs/          SPEC.md, COMPLIANCE.md, RUNBOOK.md
seed/          the demo screenplay scene
```

## Working agreement

- Small commits, present tense, describe the behavior change.
- New env var → add to `.env.example` and RUNBOOK.md in the same commit.
- Before adding any dependency, check it against constraint 1.
- Prefer boring, readable Python. Judges read this repo.
