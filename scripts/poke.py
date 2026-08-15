#!/usr/bin/env python
"""
poke.py — a scratchpad for prodding Parallel and Gemini until you trust them.

This is a development tool, not part of the app. Its job is to show you the
REAL shape of every response so you can build against what actually comes back
instead of what you assumed would.

    python scripts/poke.py check
    python scripts/poke.py compliance
    python scripts/poke.py models
    python scripts/poke.py gemini "say hello"
    python scripts/poke.py search "Determine whether Rhapsody in Blue is public domain"
    python scripts/poke.py monitors
    python scripts/poke.py monitor-create "Gershwin estate rights news" --dry-run

Add --raw to any command to dump the full response object instead of a summary.
"""

import argparse
import json
import os
import sys
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ──────────────────────────────────────────────────────────
# output helpers
# ──────────────────────────────────────────────────────────

def ok(msg):   print(f"  \033[32m✓\033[0m {msg}")
def bad(msg):  print(f"  \033[31m✗\033[0m {msg}")
def warn(msg): print(f"  \033[33m!\033[0m {msg}")
def head(msg): print(f"\n\033[1m{msg}\033[0m")


def dump(obj):
    """Best-effort JSON dump of an SDK response object."""
    for attr in ("model_dump", "dict", "to_dict"):
        if hasattr(obj, attr):
            try:
                print(json.dumps(getattr(obj, attr)(), indent=2, default=str))
                return
            except Exception:
                pass
    print(json.dumps(obj, indent=2, default=str) if isinstance(obj, (dict, list))
          else repr(obj))


# ──────────────────────────────────────────────────────────
# clients
# ──────────────────────────────────────────────────────────

def parallel_client():
    key = os.getenv("PARALLEL_API_KEY")
    if not key:
        bad("PARALLEL_API_KEY is not set. Put it in .env or the environment.")
        sys.exit(1)
    from parallel import Parallel
    return Parallel(api_key=key)


def gemini_client():
    from google import genai
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
    if use_vertex:
        return genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        bad("No Vertex config and no API key. Set GOOGLE_GENAI_USE_VERTEXAI=true "
            "plus GOOGLE_CLOUD_PROJECT, or set GEMINI_API_KEY.")
        sys.exit(1)
    return genai.Client(api_key=key)


def model_name():
    return os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


# ──────────────────────────────────────────────────────────
# commands
# ──────────────────────────────────────────────────────────

def cmd_check(args):
    """Preflight. Makes no network calls — just tells you what's configured."""
    head("Environment")
    for var in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION",
                "GOOGLE_GENAI_USE_VERTEXAI", "GEMINI_MODEL"):
        val = os.getenv(var)
        (ok if val else warn)(f"{var} = {val or '(unset)'}")

    key = os.getenv("PARALLEL_API_KEY")
    (ok if key else bad)(
        f"PARALLEL_API_KEY = {key[:8] + '…' if key else '(unset)'}")

    head("Packages")
    for pkg, label in (("parallel", "parallel-web"),
                       ("google.genai", "google-genai"),
                       ("google.adk", "google-adk")):
        try:
            __import__(pkg)
            ok(f"{label} importable")
        except ImportError:
            bad(f"{label} NOT installed")

    head("Credentials")
    try:
        import google.auth
        creds, proj = google.auth.default()
        ok(f"application default credentials found (project: {proj})")
    except Exception as e:
        bad(f"no ADC — run: gcloud auth application-default login  ({e})")


def cmd_compliance(args):
    """
    TASK 4: Prohibition 3 Compliance Scan.
    Checks backend/ and frontend/ for hardcoded domain content terms from all seed files.
    """
    head("Prohibition 3 Compliance Check")
    forbidden_terms = [
        "Nighthawks", "Wabash", "Pendelton", "Veloce", "Hopper",
        "Beaumont", "Savannah", "Kestrel", "Hokusai", "Delacroix",
        "Voss", "Okonkwo", "Rhapsody", "Dayton", "Kanagawa"
    ]
    pattern = re.compile("|".join(forbidden_terms), re.IGNORECASE)

    root_dir = os.path.join(os.path.dirname(__file__), "..")
    target_dirs = ["backend", "frontend"]

    violations = []
    for tdir in target_dirs:
        path = os.path.join(root_dir, tdir)
        if not os.path.exists(path):
            continue
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith((".py", ".js", ".html", ".css")):
                    fpath = os.path.join(root, file)
                    relpath = os.path.relpath(fpath, root_dir)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, 1):
                                m = pattern.search(line)
                                if m:
                                    violations.append((relpath, idx, m.group(0), line.strip()))
                    except Exception as e:
                        warn(f"Could not read {relpath}: {e}")

    if violations:
        bad(f"FOUND {len(violations)} PROHIBITION-3 VIOLATIONS:")
        for relpath, line_no, term, content in violations:
            print(f"  \033[31m{relpath}:{line_no}\033[0m -> term '{term}': {content[:80]}")
        sys.exit(1)
    else:
        ok(f"CLEAN! Zero hardcoded domain literals found across backend/ and frontend/ ({len(forbidden_terms)} seed terms checked).")


def cmd_models(args):
    """List models your project can actually reach. Settles the naming question."""
    client = gemini_client()
    head("Available models")
    count = 0
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        if args.all or not actions or "generateContent" in actions:
            print(f"  {m.name}")
            count += 1
    print(f"\n  {count} shown. Set GEMINI_MODEL in .env to one of these.")


def cmd_gemini(args):
    client = gemini_client()
    head(f"Gemini · {model_name()}")
    resp = client.models.generate_content(
        model=model_name(),
        contents=args.prompt,
    )
    if args.raw:
        dump(resp)
    else:
        print(resp.text)


def cmd_search(args):
    client = parallel_client()
    queries = args.query or [args.objective[:100]]

    head("Parallel Search")
    print(f"  objective      : {args.objective}")
    print(f"  search_queries : {queries}")
    print(f"  mode           : {args.mode}\n")

    resp = client.search(
        objective=args.objective,
        search_queries=queries,
        mode=args.mode,
    )

    if args.raw:
        dump(resp)
        return

    print(f"  search_id: {getattr(resp, 'search_id', '?')}")
    print(f"  results  : {len(resp.results)}\n")
    for i, r in enumerate(resp.results[: args.limit], 1):
        print(f"  \033[1m{i}. {r.title}\033[0m")
        print(f"     {r.url}")
        if getattr(r, "publish_date", None):
            print(f"     published: {r.publish_date}")
        for ex in (r.excerpts or [])[:1]:
            snippet = ex.replace("\n", " ")[:220]
            print(f"     \033[2m{snippet}…\033[0m")
        print()

    if getattr(resp, "warnings", None):
        warn(f"warnings: {resp.warnings}")


def cmd_monitors(args):
    client = parallel_client()
    head("Monitors")
    try:
        resp = client.monitor.list()
    except Exception as e:
        bad(f"list failed: {e}")
        return
    if args.raw:
        dump(resp)
        return
    items = getattr(resp, "monitors", None) or getattr(resp, "data", None) or resp
    if not items:
        print("  (none)")
        return
    for m in items:
        print(f"  {getattr(m, 'monitor_id', '?')}  "
              f"{getattr(m, 'status', '?'):8}  "
              f"{getattr(m, 'frequency', '?'):4}  "
              f"{(getattr(m, 'settings', {}) or {}).get('query', '')}")


def cmd_monitor_create(args):
    payload = {
        "type": "event_stream",
        "frequency": args.frequency,
        "processor": args.processor,
        "settings": {"query": args.query},
    }
    base = os.getenv("PUBLIC_BASE_URL", "")
    if base and not base.startswith("http://localhost"):
        payload["webhook"] = {
            "url": f"{base}/api/clearance/webhooks/monitor",
            "event_types": ["monitor.event.detected"],
        }
    else:
        warn("PUBLIC_BASE_URL is unset or localhost — creating without a webhook. "
             "Parallel cannot reach localhost; you need a deployed URL for push.")

    head("Monitor create")
    print(json.dumps(payload, indent=2))

    if args.dry_run:
        print("\n  --dry-run: nothing sent.")
        return

    client = parallel_client()
    resp = client.monitor.create(**payload)
    print()
    dump(resp) if args.raw else ok(f"monitor_id: {resp.monitor_id}")
    warn("Monitors cost money while active. Cancel it when you're done poking.")


# ──────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        prog="poke.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw", action="store_true", help="dump the full response")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="preflight env and credentials").set_defaults(fn=cmd_check)
    sub.add_parser("compliance", help="check backend/ and frontend/ for hardcoded seed terms").set_defaults(fn=cmd_compliance)

    m = sub.add_parser("models", help="list reachable Gemini models")
    m.add_argument("--all", action="store_true", help="include non-generative models")
    m.set_defaults(fn=cmd_models)

    g = sub.add_parser("gemini", help="one-shot prompt")
    g.add_argument("prompt")
    g.set_defaults(fn=cmd_gemini)

    s = sub.add_parser("search", help="Parallel Search")
    s.add_argument("objective", help="natural-language goal, not keywords")
    s.add_argument("-q", "--query", action="append", help="repeatable search query")
    s.add_argument("--mode", default="advanced", choices=["advanced", "turbo", "basic"])
    s.add_argument("--limit", type=int, default=5)
    s.set_defaults(fn=cmd_search)

    sub.add_parser("monitors", help="list monitors").set_defaults(fn=cmd_monitors)

    mc = sub.add_parser("monitor-create", help="create a monitor")
    mc.add_argument("query")
    mc.add_argument("--frequency", default="1d", choices=["1h", "1d", "1w"])
    mc.add_argument("--processor", default="lite", choices=["lite", "base"])
    mc.add_argument("--dry-run", action="store_true")
    mc.set_defaults(fn=cmd_monitor_create)

    args = p.parse_args()
    try:
        args.fn(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print()
        bad(f"{type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
