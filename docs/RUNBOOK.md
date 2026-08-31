# Setup runbook

Everything here runs on **your** machine — Windows, from `C:\Projects\NeuroForge\ClearFrame`. Work top to bottom; each section ends with something you can verify.

---

## 0. Do this first — it has a deadline

Request the **$100 Google Cloud credit**: https://forms.gle/XPe837tzogh8L5sX6

Deadline **31 Aug 2026, 11:59pm PST**. Approval takes 1–5 business days and is not guaranteed. Do it before anything else so the clock runs in the background.

While you're there, register for the hackathon itself if you haven't: https://agentic-cinema.devpost.com/register

---

## 1. Prerequisites

```powershell
python --version      # need 3.11+
git --version
gcloud --version      # if missing: https://cloud.google.com/sdk/docs/install
```

Node 20+ is required for Gemini CLI (22.x LTS recommended):

```powershell
node --version
```

Gemini CLI setup is section 6a — it changed in mid-2026 and needs its own steps.

---

## 2. Google Cloud project

```powershell
gcloud auth login

# create the project — pick a globally unique id
gcloud projects create clearframe-2026 --name="CLEARFRAME"
gcloud config set project clearframe-2026
```

Link billing. Free-trial credits still require a billing account attached; you won't be charged while credits cover usage.

```powershell
gcloud billing accounts list
gcloud billing projects link clearframe-2026 --billing-account=BILLING_ACCOUNT_ID
```

Enable the APIs:

```powershell
gcloud services enable `
  aiplatform.googleapis.com `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  storage.googleapis.com `
  firestore.googleapis.com `
  secretmanager.googleapis.com
```

Application default credentials, so the SDKs authenticate locally without a key file:

```powershell
gcloud auth application-default login
```

**Use ADC, not a downloaded service-account JSON.** No key file on disk means no key file to accidentally commit to a public repo.

Verify:

```powershell
gcloud services list --enabled | Select-String "aiplatform|run|firestore"
```

---

## 3. Storage and database

```powershell
# bucket for uploaded screenplays
gcloud storage buckets create gs://clearframe-scripts --location=us-central1 --uniform-bucket-level-access

# Firestore in native mode
gcloud firestore databases create --location=us-central1 --type=firestore-native
```

---

## 4. Parallel

1. Sign up and generate an API key: https://platform.parallel.ai
2. Try it in the [Playground](https://platform.parallel.ai) first — get a feel for how `objective` differs from a keyword query before writing code against it.

Sanity check from the terminal:

```powershell
$env:PARALLEL_API_KEY="your-key"
curl.exe https://api.parallel.ai/v1/search `
  -H "Content-Type: application/json" `
  -H "x-api-key: $env:PARALLEL_API_KEY" `
  -d '{\"objective\":\"Determine the public domain status of the composition Rhapsody in Blue by George Gershwin\",\"search_queries\":[\"Rhapsody in Blue copyright public domain\"]}'
```

You should get back `results[]` with `excerpts`. If so, both dependencies are live.

---

## 5. Local environment

```powershell
copy .env.example .env
```

Fill in `.env`:

- `GOOGLE_CLOUD_PROJECT` — your project id
- `PARALLEL_API_KEY` — from step 4
- leave the rest at defaults for now

Then:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

**Confirm `.env` is ignored before you commit anything:**

```powershell
git check-ignore -v .env
```

If that prints nothing, stop and fix `.gitignore`.

---

## 6. Git and GitHub

The repo must be public with a detectable Apache-2.0 license, and — per the rules — must contain **no commit dated before 27 July 2026**. Initialize fresh here; do not copy any history in.

```powershell
git init
git add .
git commit -m "Initial commit: project spec, compliance checklist, scaffold"

gh repo create clearframe --public --source=. --push
```

Then open the repo page and **confirm "Apache-2.0" appears in the About sidebar on the right.** The rules call this out specifically and Stage One screening is automated. If it doesn't show, GitHub hasn't detected the license file — check it's named exactly `LICENSE` at the repo root.

---

## 7. First real milestone

Before building anything, prove both dependencies work together. Write `backend/smoke.py` that:

1. calls Gemini via `google-genai` and prints a response
2. calls Parallel Search via `parallel-web` and prints a result title and URL

If both print, the foundation is real and everything after is just work. If either fails, fix it now — debugging auth underneath a half-built agent is miserable.

---

## 6a. Gemini CLI

**Read this before installing — the auth story changed in mid-2026.**

Google announced Antigravity CLI (`agy`, closed-source Go binary) on 19 May 2026 and **ended free Google-account sign-in for the open-source Gemini CLI on 18 June 2026**. Paid API keys and Vertex AI credentials were not affected.

So there are two paths, and for this project one is clearly better:

| Path | Verdict |
|---|---|
| **Gemini CLI + Vertex AI credentials** | **Use this.** Still open source, real quota, and it bills to the GCP project you just created — which the $100 hackathon credit covers. Nothing extra to sign up for. |
| Antigravity CLI (`agy`) | Free tier is ~20 agent requests/day as of July 2026, which won't survive a build like this. Closed source. Skip it. |

Install:

```powershell
npm install -g @google/gemini-cli
gemini --version
```

Point it at Vertex AI on your hackathon project. You already ran `gcloud auth application-default login` in section 2, so credentials are in place:

```powershell
setx GOOGLE_GENAI_USE_VERTEXAI "true"
setx GOOGLE_CLOUD_PROJECT "clearframe-2026"
setx GOOGLE_CLOUD_LOCATION "us-central1"
```

`setx` persists but **does not affect the current shell** — open a new terminal before continuing.

Verify:

```powershell
gemini -p "Reply with OK and nothing else."
```

If that returns `OK`, you're authenticated against Vertex and billing to the hackathon project. If it asks you to sign in with a Google account, the env vars didn't take — confirm you opened a fresh terminal.

### Parallel Search MCP (optional, recommended)

`.gemini/settings.json` in this repo already wires up Parallel's hosted Search MCP, which gives Gemini CLI live web search and URL fetching while it builds. It's free and needs no API key. Restart `gemini` after any config change, then run `/mcp` to confirm `web_search` and `web_fetch` are listed.

> **This does not satisfy the Parallel track requirement.** The MCP is a development convenience. The rules require the *project* to call Parallel's Search API at runtime via the `parallel-web` SDK, in code, on the live request path. Wiring the MCP into your editor proves nothing to the judges. Keep the two separate in your head.

---

## 8. Handing off to Gemini CLI

From the project root:

```powershell
gemini
```

It picks up `GEMINI.md` automatically, which carries the constraints, the stack, and the design rules. Point it at `docs/SPEC.md` §9 for build order.

Good opening prompt:

> Read GEMINI.md and docs/SPEC.md. Implement step 1 of the build order in SPEC.md §9: a smoke test at backend/smoke.py that calls Gemini via google-genai and Parallel Search via parallel-web, printing a result from each. Do not add any dependency not already in backend/requirements.txt.

---

## Deploying later

Not needed until the app runs locally, but for reference:

```powershell
gcloud run deploy clearframe `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars "GOOGLE_CLOUD_PROJECT=clearframe-2026,GOOGLE_GENAI_USE_VERTEXAI=true" `
  --set-secrets "PARALLEL_API_KEY=parallel-api-key:latest"
```

Store the Parallel key in Secret Manager rather than passing it as a plain env var:

```powershell
echo -n "your-key" | gcloud secrets create parallel-api-key --data-file=-
```

`--allow-unauthenticated` is required — the hosted URL must be reachable by judges without a login.

The Cloud Run URL becomes `PUBLIC_BASE_URL`, and the Parallel Monitor webhook target is `$PUBLIC_BASE_URL/webhooks/monitor`. Monitor can't reach `localhost`, so the webhook half of the project can only be tested once deployed — factor that into the schedule.

---

## 9. Model Harmonization & Quota Architecture

### Standardized Model: `gemini-3.1-flash-lite`
All configuration files (`.env`, `.env.example`, `backend/clients.py`) standardize on `GEMINI_MODEL=gemini-3.1-flash-lite`. Model-hopping across files is prohibited.

### 3-Call Quota Optimization
To remain cleanly within Gemini Free Tier limits (20 requests/day per model) during development and testing:
1. **Intake Phase**: 1 call (`parse_script_scenes`)
2. **Extraction Phase**: 1 call (`extract_clearable_elements`)
3. **Batch Research Phase**: 1 call (`batch_research_elements_parallel`) containing Parallel search excerpts mapped per `element_id`.

Total Gemini spend per clearance run is **3 API calls** regardless of element count.

### Parallel Monitor Controls & Credit Protection
To prevent accidental monitor credit exhaustion during local development or test suites:
- `ENABLE_PARALLEL_MONITORS=false`: Disables live monitor creation during local testing while preserving report generation and typing.
- `PARALLEL_MONITOR_MAX_COUNT=5`: Caps the number of live monitors created per script analysis to prevent runaway quota consumption.
- On Cloud Run production deployment for judging, set `ENABLE_PARALLEL_MONITORS=true`.

### Process Restart Protocol
Any modification to `.env` or files under `backend/` requires a full process kill and relaunch of the server (`uvicorn backend.api.main:app`). Never test against a running process after backend edits.

