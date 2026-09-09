#!/usr/bin/env python3
"""
generate_mobility_wiki.py — Mobility & Micromobility Process Wiki generator.

Repo:  https://github.com/ghatk047/mobility-wiki
Pages: https://ghatk047.github.io/mobility-wiki/

Flags
  (none)          pilot — the first process in catalogue order
  --full          all incomplete processes
  --count N       next N incomplete
  --pid PID       single process, e.g. --pid MM-MD-DM-01
  --start PID     resume from PID in catalogue order
  --force         regenerate even if the tracker marks it Complete
  --no-verify     skip the live-page verification wait
  --bootstrap     push shell only (.nojekyll, css, js, indexes) and exit
  --rebuild-nav   regenerate and push every index, no model calls
  -j, --parallel N  run N processes concurrently (default 1)
  --dry-run       list what would run, generate nothing

Secrets come from the environment only, never from a file:
    export GITHUB_TOKEN=$(gh auth token)
    export OPENROUTER_API_KEY=...        # only if a domain is routed to openrouter
"""

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from base64 import b64encode
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taxonomy import (  # noqa: E402
    L1_META, TIER_LABEL, L1_ARCHETYPES, TAXONOMY, PROCESSES, BY_PID,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

REPO_OWNER = "ghatk047"
REPO_NAME  = "mobility-wiki"
BRANCH     = "main"
PAGES_BASE = f"https://{REPO_OWNER}.github.io/{REPO_NAME}"
GH_API     = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents"

SITE_TITLE = "Mobility &amp; Micromobility Process Wiki"
SITE_SUB   = "Ride-Hail &bull; Autonomous &bull; Delivery &bull; Micromobility &bull; Air Mobility"

# Stamped as an HTML comment in every generated page. Bump when the shell changes
# so a later pass can find and re-render stale pages.
TEMPLATE_VERSION = "1.0.0"

DISCLAIMER = (
    "Independently compiled from public sources. Not affiliated with, sponsored by, "
    "or endorsed by Uber, Lyft, Waymo, DoorDash, Bird, Lime, Bolt, Joby Aviation, "
    "Archer Aviation, Wisk, Zipline, Wing, or Amazon &mdash; illustrative of mobility "
    "and micromobility industry archetypes."
)

# ── Model backends ──────────────────────────────────────────────────────────
OLLAMA_URL     = "http://localhost:11434"
PRIMARY_MODEL  = "qwen2.5-coder:14b"
FALLBACK_MODEL = "qwen2.5:latest"
OLLAMA_TIMEOUT = 600

OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
OPENROUTER_TIMEOUT = 300

# Per-L1-domain backend routing. Every domain defaults to the free local model.
# AM and DD are the only candidates for an "openrouter" override, and only on
# explicit approval — OpenRouter costs real money per token.
BACKEND_CONFIG = {code: "ollama" for code in L1_META}

ROOT        = Path(__file__).resolve().parent.parent
DATA_DIR    = ROOT / "data"
DIAGRAM_DIR = ROOT / "diagrams"
IMG_DIR     = ROOT / "assets" / "img"
REG_DIR     = ROOT / "registries"
TRACKER     = DATA_DIR / "processes.json"          # local only, never pushed
EXCEL_PATH  = DATA_DIR / "Mobility_Process_Wiki.xlsx"   # local only, never pushed

# A system-resident sans stack. An SVG loaded through <img> cannot fetch a
# webfont, so anything exotic silently falls back to serif and looks soft.
FONT_STACK = "Helvetica Neue, Helvetica, Arial, sans-serif"
# fontFamily MUST be at the top level of the init config. Mermaid v11 silently
# ignores it inside themeVariables and falls back to "trebuchet ms" — verified by
# rendering both forms through mmdc 11.12.0.
INIT_LINE = ("%%{init: {'theme':'base','fontFamily':'" + FONT_STACK + "',"
             "'themeVariables':{'fontSize':'13px'}}}%%")

PID_W, PID_H = 2400, 1400
EA_W,  EA_H  = 3840, 2160
MMDC_SCALE   = 2
VERIFY_WAIT  = 90

DEPTH_PROCESS, DEPTH_L2, DEPTH_L1 = 3, 2, 1
DEPTH_EA, DEPTH_EA_IDX = 2, 1

GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "").strip()
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()

EA_DIR_SLUG = "ea-diagrams"

EA_DIAGRAMS = [
    ("ea-01", "Mobility Platform System Landscape",
     "The full marketplace estate across all 18 domains — matching and dispatch, pricing, "
     "payments, trust and safety, and the ML platform beneath them"),
    ("ea-02", "Marketplace Matching and Dispatch Architecture",
     "Demand signal through supply positioning, assignment, routing and ETA prediction "
     "across ride-hail, delivery and micromobility"),
    ("ea-03", "Autonomous Ride-Hail Operations Architecture",
     "Waymo-archetype driverless operations — depot, dispatch, remote assistance and the "
     "regulatory reporting boundary. Production AV stack is trade secret and renders sparse"),
    ("ea-04", "Micromobility Fleet and IoT Architecture",
     "Vehicle telemetry, charging and rebalancing through to MDS and GBFS feeds consumed "
     "by municipal compliance platforms"),
    ("ea-05", "Last-Mile Delivery Platform Architecture",
     "Merchant POS integration through order injection, courier dispatch, autonomous "
     "delivery modes and consumer handoff"),
    ("ea-06", "Trust, Safety and Insurance Data Flow",
     "Background screening through in-trip safety signals, incident response, claims and "
     "regulatory transparency reporting"),
    ("ea-07", "Payments and Payout Architecture",
     "Consumer authorisation through marketplace settlement, contractor payout rails and "
     "1099 tax reporting"),
    ("ea-08", "eVTOL Certification and Vertiport Operations Architecture",
     "Type certification pathway, Part 135 air carrier operations, vertiport turnaround and "
     "PSU airspace integration. Pre-commercial — much of this renders sparse"),
    ("ea-09", "Drone Delivery and BVLOS Airspace Architecture",
     "Order eligibility through nest operations, USS strategic deconfliction under ASTM "
     "F3548 and package handoff"),
    ("ea-10", "Regulatory and Municipal Compliance Data Flow",
     "TNC permits, municipal scooter programmes, MDS data sharing, AV disengagement "
     "reporting and privacy controls"),
]


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

def log(msg, level="INFO"):
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {level:<5} {msg}", flush=True)


def dump_raw(tag, raw):
    """Save an unparseable model response for inspection."""
    try:
        d = DATA_DIR / "raw"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{tag}.txt"
        f.write_text(raw or "(empty response)", encoding="utf-8")
        log(f"  raw response saved to {f}", "WARN")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRIES — research-grounded facts, injected into prompts and validated after
# ─────────────────────────────────────────────────────────────────────────────

def _load_registry(name):
    p = REG_DIR / f"{name}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"registry {name}.json unreadable: {exc}", "ERROR")
        return {}


REG_COMPANIES   = _load_registry("companies")
REG_SYSTEMS     = _load_registry("systems")
REG_REGULATIONS = _load_registry("regulations")
REG_KPIS        = _load_registry("kpis")
REG_ROLES       = _load_registry("roles")


def registry_systems_for(l1):
    """Systems from the archetype slices this L1 domain speaks to."""
    out = []
    for arch in L1_ARCHETYPES.get(l1, []):
        out.extend(REG_SYSTEMS.get("systems", {}).get(arch, []))
    return out


def registry_regs_for(l1):
    return [r for r in REG_REGULATIONS.get("regulations", [])
            if l1 in r.get("domain", [])]


def registry_companies_for(l1):
    archs = set(L1_ARCHETYPES.get(l1, []))
    return [c for c in REG_COMPANIES.get("companies", [])
            if c.get("archetype") in archs]


def sparse_layers_for(l1):
    archs = set(L1_ARCHETYPES.get(l1, []))
    return [s for s in REG_SYSTEMS.get("sparse_layers", [])
            if s.get("archetype") in archs]


def registry_brief(l1):
    """Compact, prompt-ready grounding block for one L1 domain."""
    lines = []

    comps = registry_companies_for(l1)
    if comps:
        lines.append("VERIFIED 2026 COMPANY STATUS — these facts override your training data:")
        for c in comps:
            lines.append(f"  * {c['name']} [{c['sourcing']}] — {c['status_2026']}")
            for f in c.get("facts", [])[:4]:
                lines.append(f"      - {f}")
            if c.get("modelling_note"):
                lines.append(f"      NOTE: {c['modelling_note']}")
            if c.get("sparse_note"):
                lines.append(f"      SPARSE: {c['sparse_note']}")

    syss = registry_systems_for(l1)
    if syss:
        lines.append("\nREAL SYSTEMS — use ONLY these names, do not invent product names:")
        for s in syss:
            lines.append(f"  * {s['name']} ({s['vendor']}) — {s['capability']}")

    sparse = sparse_layers_for(l1)
    if sparse:
        lines.append("\nGENUINELY UNDOCUMENTED LAYERS — do NOT invent names or specifics here. "
                     "If a step touches one of these, describe the FUNCTION and say sourcing is limited:")
        for s in sparse:
            lines.append(f"  * {s['layer']} — {s['evidence_gap']}")

    regs = registry_regs_for(l1)
    if regs:
        lines.append("\nREAL REGULATORY CITATIONS — cite only these, exactly as written:")
        for r in regs:
            caveat = ""
            if r.get("must_be_labelled_proposed"):
                caveat = "  << MUST be described as PROPOSED and NOT IN FORCE >>"
            lines.append(f"  * {r['citation']} — {r['title']} [{r['status']}]{caveat}")

    kpis = REG_KPIS.get("kpis", {}).get(l1, [])
    if kpis:
        lines.append("\nREAL KPI PATTERNS for this domain:")
        for k in kpis:
            v = f" = {k['value']}" if k.get("value") else ""
            lines.append(f"  * {k['name']} ({k['unit']}) [{k['type']}]{v}")
        lines.append("  Metrics marked 'pattern' have no published baseline — use the metric "
                     "NAME with a plausible target, never present an invented number as sourced.")

    roles = REG_ROLES.get("roles", {}).get(l1, [])
    if roles:
        lines.append("\nREAL ROLE TITLES for this domain: " + ", ".join(roles))

    return "\n".join(lines)


def validate_process(proc, data):
    """Log any system, regulation or role a generated page names that isn't sourced."""
    l1 = proc["l1"]
    known_sys = {s["name"].lower() for s in registry_systems_for(l1)}
    known_sys |= {s["name"].lower() for s in REG_SYSTEMS.get("systems", {}).get("shared-enterprise", [])}
    known_roles = {r.lower() for r in REG_ROLES.get("roles", {}).get(l1, [])}
    known_regs = [r["citation"].lower() for r in REG_REGULATIONS.get("regulations", [])]

    unknown_sys, unknown_roles = set(), set()
    for s in data.get("l4_steps", []):
        sysname = str(s.get("system", "")).strip()
        if sysname and not any(k in sysname.lower() or sysname.lower() in k for k in known_sys):
            unknown_sys.add(sysname)
        role = str(s.get("role", "")).strip()
        if role and not any(k in role.lower() or role.lower() in k for k in known_roles):
            unknown_roles.add(role)
    for s in data.get("systems", []):
        s = str(s).strip()
        if s and not any(k in s.lower() or s.lower() in k for k in known_sys):
            unknown_sys.add(s)

    blob = json.dumps(data).lower()
    # \b after each keyword: without it the "ab" alternative matched "above",
    # "part" matched "partial", and every page reported phantom citations.
    cited = re.findall(
        r'\b(?:14\s+cfr|cfr|part|prop\b|proposition|ab|astm|cpuc)\b[\s.]*'
        r'(?:no\.?\s*)?(\d[\w.\-]*)', blob)
    cited = [c for c in cited if any(ch.isdigit() for ch in c)]
    unknown_regs = {c for c in set(cited)
                    if not any(c in k for k in known_regs)}

    if unknown_sys:
        log(f"  VALIDATION {proc['pid']}: {len(unknown_sys)} unsourced system(s): "
            f"{', '.join(sorted(unknown_sys)[:6])}", "WARN")
    if unknown_roles:
        log(f"  VALIDATION {proc['pid']}: {len(unknown_roles)} off-registry role(s): "
            f"{', '.join(sorted(unknown_roles)[:6])}", "WARN")
    if unknown_regs:
        log(f"  VALIDATION {proc['pid']}: {len(unknown_regs)} unrecognised citation-like "
            f"token(s): {', '.join(sorted(unknown_regs)[:6])}", "WARN")
    if not (unknown_sys or unknown_roles or unknown_regs):
        log(f"  VALIDATION {proc['pid']}: clean — all systems, roles and citations sourced")
    return {"unknown_systems": sorted(unknown_sys),
            "unknown_roles": sorted(unknown_roles),
            "unknown_regs": sorted(unknown_regs)}


# ─────────────────────────────────────────────────────────────────────────────
# MERMAID SANITISER
#
# Ported from shipping-wiki, where every one of these steps was a shipped defect.
# The stash/restore around the digit-leading-node-ID fix is the important part:
# without it the rule that turns `1.1` into `S1_1` also mangles `FAA Part 135`,
# `49 CFR 107.31`, `ASTM F3548-21` and `CPUC Decision 18-05-043`.
# ─────────────────────────────────────────────────────────────────────────────

def sanitise_mermaid(mmd_str):
    if not mmd_str:
        return None
    # 1. Strip markdown fences
    mmd_str = re.sub(r'^```[a-z]*\n?', '', mmd_str, flags=re.MULTILINE)
    mmd_str = re.sub(r'```$', '', mmd_str, flags=re.MULTILINE)
    # 2. Remove YAML frontmatter
    mmd_str = re.sub(r'^---.*?---\s*', '', mmd_str, flags=re.DOTALL)
    # 3. Fix HTML-encoded arrows
    mmd_str = mmd_str.replace('--gt;', '-->').replace('--&gt;', '-->').replace('--&gt', '-->')
    # 3b. HTML line breaks would lose their angle brackets in step 5
    for _tag in ('<br/>', '<br />', '<br>'):
        mmd_str = mmd_str.replace(_tag, '\\n')
    # 4. Digit-leading node IDs: 1.1 -> S1_1, with label text stashed so that
    #    real citations survive untouched.
    stash = []

    def _hold(m):
        stash.append(m.group(0))
        return f'\x00{len(stash) - 1}\x00'

    mmd_str = re.sub(r'\[[^\]]*\]|\{[^}]*\}|\|"[^"]*"\||\|[^|\n]*\|', _hold, mmd_str)
    mmd_str = re.sub(r'\b(\d+)\.(\d+)\b', r'S\1_\2', mmd_str)
    mmd_str = re.sub(r'\x00(\d+)\x00', lambda m: stash[int(m.group(1))], mmd_str)
    # 5. Strip characters that break the parser from inside labels — square
    #    brackets, curly decision diamonds and round terminators alike.
    def clean_label(m):
        text = m.group(2)
        text = re.sub(r'[()&<>]', '', text)
        text = re.sub(r'  +', ' ', text).strip()
        return f'{m.group(1)}{text}{m.group(3)}'

    # 4b. Normalise line-break escapes to exactly ONE backslash + n, which is what
    #     mermaid wants. Verified against mmdc 11.12.0: `\\n` renders a proper two-line
    #     label, `\\\\n` breaks the line but leaves a stray backslash in the text, and a
    #     lone `\\\\` with no n renders as a literal backslash and no break. Models emit
    #     all three, so every run of backslashes around an optional n is collapsed.
    #     A backslash has no other legitimate use inside a mermaid label.
    def _fix_breaks_in_label(m):
        inner = re.sub(r'\\{2,}n', r'\\n', m.group(2))     # \\n and longer -> \n
        inner = re.sub(r'\\{2,}(?!n)', r'\\n', inner)      # stray \\ with no n -> \n
        return f'{m.group(1)}{inner}{m.group(3)}'

    mmd_str = re.sub(r'(\[)([^\]]+)(\])', _fix_breaks_in_label, mmd_str)
    mmd_str = re.sub(r'(\{)([^}]+)(\})', _fix_breaks_in_label, mmd_str)
    mmd_str = re.sub(r'(\[)([^\]]+)(\])', clean_label, mmd_str)
    mmd_str = re.sub(r'(\{)([^}]+)(\})', clean_label, mmd_str)
    mmd_str = re.sub(r'(\()([^)]+)(\))', clean_label, mmd_str)
    # 5b. Drop duplicate edge statements. Models like to restate every edge in a
    #     trailing block after the subgraphs; mermaid then draws each arrow twice,
    #     which looks like a doubled line and also inflates the branch count so a
    #     thin diagram scores well. A repeated identical edge is never intentional
    #     here. Lines that also DEFINE a node shape are kept, since dropping one
    #     would lose the node's label.
    #     A line is only DROPPED when it is a bare edge (no node shape on it) and
    #     every edge it declares has already been seen. Shape-bearing lines always
    #     survive, but still register their edges so a later bare restatement of
    #     the same edge is recognised as the duplicate.
    _bare_edge = re.compile(
        r'^[A-Za-z][A-Za-z0-9_]*'
        r'(?:\s*--\s*[^->|\n]*?)?\s*-->(?:\s*\|[^|\n]*\|)?\s*'
        r'[A-Za-z][A-Za-z0-9_]*$')
    seen_edges = set()
    kept = []
    for line in mmd_str.split('\n'):
        stripped = line.strip()
        pairs = parse_edges(stripped)
        if pairs:
            is_bare = bool(_bare_edge.fullmatch(stripped))
            if is_bare and all(p in seen_edges for p in pairs):
                continue
            seen_edges.update(pairs)
        kept.append(line)
    mmd_str = '\n'.join(kept)
    # collapse the blank run a dropped trailing block leaves behind
    mmd_str = re.sub(r'\n{3,}', '\n\n', mmd_str)

    # 6. Force one canonical %%{init}%% with a system-resident font stack.
    mmd_str = re.sub(r'^\s*%%\{init.*?\}%%\s*\n?', '', mmd_str,
                     flags=re.DOTALL | re.MULTILINE)
    mmd_str = INIT_LINE + "\n" + mmd_str.lstrip()
    # 7. No blank line between %%{init}%% and the flowchart directive
    lines = mmd_str.strip().split('\n')
    cleaned = []
    for line in lines:
        if cleaned and cleaned[-1].strip().startswith('%%{init') and line.strip() == '':
            continue
        cleaned.append(line)
    return '\n'.join(cleaned).strip()


def fix_breaks(mmd):
    """HTML line breaks to Mermaid \\n, before the label cleaner strips < >."""
    if not mmd:
        return mmd
    for tag in ("<br/>", "<br />", "<br>"):
        mmd = mmd.replace(tag, "\\n")
    return mmd


# ─────────────────────────────────────────────────────────────────────────────
# MODEL BACKENDS
# ─────────────────────────────────────────────────────────────────────────────

def call_model(system_prompt, user_prompt, backend="ollama", temperature=0.35,
               model=None):
    """Single dispatch point. Everything downstream is backend-agnostic:
    the same sanitiser, the same richness scoring, the same SVG finalisation
    and the same font enforcement run whichever API produced the draft."""
    if backend == "openrouter":
        return _call_openrouter(system_prompt, user_prompt, temperature,
                                model or OPENROUTER_MODEL)
    return _call_ollama(system_prompt, user_prompt, temperature,
                        model or PRIMARY_MODEL)


def _call_ollama(system_prompt, user_prompt, temperature, model):
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": 8192},
        },
        timeout=OLLAMA_TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("response", "")


def _call_openrouter(system_prompt, user_prompt, temperature, model):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in the environment")
    r = requests.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}",
                 "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_prompt}],
            "temperature": temperature,
            "max_tokens": 4096,
        },
        timeout=OPENROUTER_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def backend_for(l1):
    return BACKEND_CONFIG.get(l1, "ollama")


def model_ladder(backend, attempt):
    """Which model to use on retry attempt N for a given backend."""
    if backend == "openrouter":
        return OPENROUTER_MODEL
    return [PRIMARY_MODEL, PRIMARY_MODEL, FALLBACK_MODEL][min(attempt, 2)]


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS — two calls, two system prompts.
#
# Call 1 returns content JSON and is explicitly forbidden from emitting Mermaid;
# a lightweight model that injects a diagram into the JSON response breaks
# extraction. Call 2 returns raw Mermaid only, so a multi-line label never has to
# survive JSON string escaping — which is where \n gets flattened.
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_JSON = """You are a senior operations and enterprise architecture consultant \
specialising in mobility platforms. Your expertise spans six distinct operating models that \
share a marketplace and dispatch core:

- Ride-hail marketplaces (Uber, Lyft) — two-sided matching, surge pricing, 1099 supply
- Autonomous ride-hail (Waymo) — driverless fleet operations, remote assistance, AV permitting
- Last-mile delivery marketplaces (DoorDash) — merchant integration, courier dispatch, handoff
- Micromobility fleets (Bird, Lime, Bolt) — charging, rebalancing, IoT telemetry, permit compliance
- eVTOL air mobility (Joby, Archer, Wisk) — type certification, Part 135, vertiport operations
- Drone delivery (Zipline, Wing, Amazon Prime Air) — BVLOS authorisation, nest ops, deconfliction

These are genuinely different businesses. Do not describe a scooter operation as if it were a \
ride-hail marketplace, or an eVTOL programme as if it were already carrying paying passengers.

GROUNDING DISCIPLINE — this is the most important rule:
Your training data is stale on this industry. A grounding block of researched, verified 2026 \
facts is supplied with each request. Where it contradicts your training data, the grounding \
block wins. Where the grounding block marks a layer as undocumented or sparse, do NOT invent \
product names, vendor names, version numbers or metric values to fill the gap — describe the \
function and state that public sourcing is limited. A thin, honest answer is correct; a \
plausible-sounding fabrication is a failure.

Return ONLY valid JSON with no markdown fences, no preamble, no trailing text and \
absolutely no Mermaid or diagram syntax anywhere in the response."""

MERMAID_RULES = """MERMAID CRITICAL RULES (violations cause mmdc parse errors):
- NO YAML frontmatter, no markdown fences, no commentary
- Node IDs MUST start with a LETTER such as NodeA, StepB or S1_1 — never a digit
- Arrows are ALWAYS --> and never --gt or --&gt;
- Node labels contain NO parentheses, no ampersand, no angle brackets
- Never use <br/> for a line break — use a literal backslash-n"""

SYSTEM_PROMPT_MMD = """You are a senior business process architect who draws BPMN and \
enterprise architecture diagrams in Mermaid for mobility and micromobility platforms.

You output raw Mermaid source and nothing else. No JSON. No fences. No explanation.

Your diagrams are dense and operationally real: multiple phases, genuine decision points with \
both branches labelled in real domain language, rework loops that route failures back to \
earlier work rather than straight to an exit, and two-line labels naming both the activity and \
the system or document involved.

""" + MERMAID_RULES

JSON_SHAPE = """{
  "description": "3-4 sentence operational description naming the archetype this applies to",
  "trigger": "what initiates this process",
  "outcome": "what successful completion produces",
  "archetype_notes": "1-2 sentences on how this process differs across the archetypes it touches",
  "sourcing_confidence": "solid or partial or sparse",
  "l4_steps": [
    {
      "step": "1.1",
      "name": "Step name",
      "role": "Exact role from the supplied role list",
      "system": "Exact system from the supplied systems list",
      "input": "Input document or data",
      "output": "Output document or deliverable",
      "kpi": "Measurable metric with target",
      "decision_point": "Y or N",
      "exception": "Y or N",
      "pain_point": "Real operational challenge at this step"
    }
  ],
  "swim_lanes": [{"role": "Role Title", "color": "#hex", "steps": ["1.1", "1.2"]}],
  "systems": ["System A", "System B"],
  "kpis": ["Match time under 15 seconds", "Driver acceptance rate above 70 percent"],
  "risks": ["Specific operational, regulatory, safety or commercial risk"]
}"""

CONTENT_RULES = """CONTENT RULES:
- 10 to 12 l4_steps spread across 5 or 6 phases, numbered by phase: 1.1, 1.2,
  then 2.1, 2.2, then 3.1 and so on. Do NOT number every step 1.x
- At least 3 steps must be genuine decision points with decision_point Y
- At least 2 steps must have exception Y
- Roles must come from the supplied role list for this domain
- 4 to 6 systems, every one from the supplied systems list
- 4 to 6 KPIs drawn from the supplied KPI patterns, with measurable targets
- 3 to 5 risks covering regulatory, safety, commercial and operational categories
- sourcing_confidence must be "sparse" if this process depends on an undocumented layer
- Do NOT include a mermaid field. The diagram is requested separately.
- JSON ONLY — no markdown, no preamble"""

# Form reference for the BPMN diagram. Deliberately from a DIFFERENT industry
# (airline crew resourcing, lifted from the sibling repo) so the model copies the
# CONSTRUCT and never the subject matter.
BPMN_FORM_EXAMPLE = """flowchart LR
  subgraph P1[Phase 1: Request and Screening]
    A([Start]) --> B[Receive crew requisition\\nSuccessFactors]
    B --> C{Gap above\\nrecruitment threshold?}
    C -- No --> B
    C -- Yes --> D[Publish vacancy and\\nbuild candidate pipeline]
  end

  subgraph P2[Phase 2: Assessment]
    D --> E[Screen against\\nFAR 121 ATP minimums]
    E --> F{Meets minimums?}
    F -- No --> Rej1([Decline])
    F -- Yes --> G[Simulator assessment\\nFFS Level D]
    G --> H{Sim result\\npass or fail?}
    H -- Fail --> Rej1
  end

  subgraph P3[Phase 3: Clearance and Offer]
    H -- Pass --> I[Background and\\nmedical screening]
    I --> J{All clearances\\nreceived?}
    J -- No --> Hold1([Hold])
    J -- Yes --> K[Issue contract and\\nconfirm class date]
  end

  subgraph P4[Phase 4: Onboarding]
    K --> L[Schedule ground school\\nand line training]
    L --> M{Training\\ncompleted?}
    M -- No --> L
    M -- Yes --> N[Release to line flying]
  end

  subgraph P5[Phase 5: Confirmation]
    N --> O[Probation review\\nand confirmation]
    O --> P{Standards met?}
    P -- No --> L
    P -- Yes --> Q([End])
  end

  style A fill:#0f2a5c,color:#fff,stroke:#0f2a5c
  style Q fill:#0f2a5c,color:#fff,stroke:#0f2a5c
  style Rej1 fill:#0f2a5c,color:#fff,stroke:#0f2a5c
  style Hold1 fill:#0f2a5c,color:#fff,stroke:#0f2a5c
  style C fill:#10b3c6,color:#fff,stroke:#10b3c6
  style F fill:#10b3c6,color:#fff,stroke:#10b3c6
  style H fill:#10b3c6,color:#fff,stroke:#10b3c6
  style J fill:#10b3c6,color:#fff,stroke:#10b3c6
  style M fill:#10b3c6,color:#fff,stroke:#10b3c6
  style P fill:#10b3c6,color:#fff,stroke:#10b3c6"""


# The anti-pattern the first generated diagram fell into: every failed decision
# dead-ends in its own exception terminator, so the "flow" is a linear checklist
# with eight exits and no rework. Shown to the model explicitly, because telling
# it to "add rework loops" in prose did not work.
BPMN_ANTIPATTERN = """WRONG — do not produce this shape:

  NodeA[Ingest data] --> DecA{Ingestion successful?}
  DecA -- Yes --> NodeB[Recognise pattern]
  DecA -- No  --> Exception1([Exception])
  NodeB --> DecB{Pattern recognised?}
  DecB -- Yes --> NodeC[Analyse supply]
  DecB -- No  --> Exception2([Exception])

Three things are wrong with it:
  1. Every No branch dead-ends in a NEW exception terminator. Nothing ever routes
     back to earlier work, so there is no rework and no cycle in the graph.
  2. The decisions are not decisions. "Ingestion successful?", "Pattern
     recognised?" and "Strategy generated?" just ask whether the previous step
     worked. That is error handling, not a business decision.
  3. It uses one exception terminator per decision. Use at MOST two or three
     terminators in the whole diagram, shared by several branches.

RIGHT — the same region done properly:

  ING[Ingest supply and demand events\\nGBFS feed and trip event stream] --> QUAL{Feed completeness\\nabove 95 percent?}
  QUAL -- No --> BACKFILL[Backfill from last known state\\nand flag degraded confidence]
  BACKFILL --> ING
  QUAL -- Yes --> FCST[Generate short-horizon forecast\\nMichelangelo online prediction]
  FCST --> ACC{Forecast error inside\\ntolerance band?}
  ACC -- No --> RETRAIN[Trigger retraining and\\nfall back to baseline model]
  RETRAIN --> FCST
  ACC -- Yes --> POS[Publish positioning guidance\\nto supply heat map]

Note what changed: BACKFILL routes back to ING and RETRAIN routes back to FCST,
so the graph contains real cycles. The decisions name a threshold and a business
condition, not "did it work". No exception terminator was needed at all here."""


def archetype_directive(proc):
    """Tier 1 is the SHARED core. Its processes must read across every archetype
    they touch, with the differences pushed into archetype_notes. The first
    generated page narrowed MM-MD-DM-01 to micromobility alone because the
    registry brief injects several archetype slices and the model latched onto
    one of them."""
    archs = L1_ARCHETYPES.get(proc["l1"], [])
    pretty = ", ".join(a.replace("-", " ") for a in archs if a != "shared-enterprise")
    if proc["tier"] == 1:
        return (
            f"ARCHETYPE SCOPE — this is a TIER 1 SHARED CORE process. It runs across "
            f"ALL of these archetypes: {pretty}.\n"
            f"  * Write the description, trigger, outcome and steps so they hold for EVERY\n"
            f"    one of those archetypes. Do NOT open with 'This process applies to the\n"
            f"    X archetype' and do not narrow the whole process to one of them.\n"
            f"  * Draw systems from MORE THAN ONE archetype slice, so the steps reflect the\n"
            f"    shared mechanism rather than one operator's stack.\n"
            f"  * Put the differences BETWEEN archetypes in archetype_notes, and only there.\n"
            f"    That field is where 'ride-hail matches drivers, micromobility rebalances\n"
            f"    vehicles, delivery assigns couriers' belongs.\n"
        )
    if proc["tier"] == 2:
        return (
            f"ARCHETYPE SCOPE — this is a TIER 2 ARCHETYPE-SPECIFIC process, particular to: "
            f"{pretty}. Write it specifically for that operating model. Do not genericise it "
            f"into a marketplace process.\n"
        )
    return (
        f"ARCHETYPE SCOPE — this is a TIER 3 CROSS-CUTTING ENTERPRISE process. It applies "
        f"across the business. Keep it archetype-neutral unless a specific archetype "
        f"materially changes the work, and note that in archetype_notes.\n"
    )


def generate_process_content(proc, attempt=0):
    """Call 1 — content JSON, no Mermaid."""
    backend = backend_for(proc["l1"])
    user = (
        f"Document this business process for the mobility and micromobility industry:\n"
        f"  Process ID : {proc['pid']}\n"
        f"  Tier       : {TIER_LABEL[proc['tier']]}\n"
        f"  L1 Domain  : {proc['l1_name']}\n"
        f"  L2 Group   : {proc['l2_name']}\n"
        f"  L3 Process : {proc['name']}\n\n"
        f"{archetype_directive(proc)}\n"
        f"GROUNDING BLOCK — verified facts, these override your training data:\n"
        f"{registry_brief(proc['l1'])}\n\n"
        f"Return exactly this JSON shape:\n{JSON_SHAPE}\n\n{CONTENT_RULES}\n"
    )
    for i in range(3):
        model = model_ladder(backend, i)
        try:
            raw = call_model(SYSTEM_PROMPT_JSON, user, backend,
                             temperature=0.3 + 0.1 * i, model=model)
            data = extract_json(raw, required=("l4_steps",))
            if not data:
                dump_raw(f"{proc['pid']}-json-{i+1}", raw)
            if data and data.get("l4_steps"):
                data.setdefault("systems", [])
                data.setdefault("kpis", [])
                data.setdefault("risks", [])
                return data
            log(f"{proc['pid']}: unusable JSON from {model} (try {i+1}/3)", "WARN")
        except Exception as exc:
            log(f"{proc['pid']}: {backend} error on {model} — {exc}", "WARN")
        time.sleep(2)
    return None


def repair_directive(prev_metrics, prev_degenerate):
    """Targeted feedback for a retry. Restating the generic rule does not work —
    qwen2.5-coder:14b produced 9 degenerate decisions and 0 substantive ones across
    three drafts of MM-MD-DM-01 with the anti-pattern example already in the prompt.
    Naming the model's own offending labels back to it does work."""
    if not prev_metrics:
        return ""
    lines = ["YOUR PREVIOUS ATTEMPT WAS REJECTED. Fix these specific problems:"]
    if prev_degenerate:
        lines.append(
            f"  * You wrote {len(prev_degenerate)} decisions that only ask whether the "
            f"previous step worked. These are BANNED. Here are the exact ones you wrote:")
        for d in prev_degenerate[:6]:
            lines.append(f"      REJECTED: {d}")
        lines.append(
            "    Every one must be REPLACED by a decision naming a threshold or a business\n"
            "    condition. Rewrite them along these lines:\n"
            "      'Data ingestion successful?'   -> 'Feed completeness above 95 percent?'\n"
            "      'Forecast validation passed?'  -> 'Forecast error within tolerance band?'\n"
            "      'Strategy generated?'          -> 'Projected utilisation above target?'\n"
            "      'Adjustment successful?'       -> 'Supply gap closed below 10 percent?'\n"
            "    Each decision label must contain a NUMBER or one of: above, below, within,\n"
            "    exceeds, breached, threshold, cap, tolerance, approved, cleared, granted,\n"
            "    eligible, compliant, triggered, detected, met, expired.")
    if prev_metrics.get("loops", 0) < PID_GATES["loops"]:
        lines.append(
            f"  * You produced only {prev_metrics.get('loops', 0)} rework loops. At least "
            f"{PID_GATES['loops']} are required. Point a failed decision back to an EARLIER "
            f"task node so the graph contains a cycle.")
    if prev_metrics.get("nodes", 99) < PID_FLOOR["nodes"]:
        lines.append(f"  * Only {prev_metrics.get('nodes')} nodes. At least "
                     f"{PID_FLOOR['nodes']} are required.")
    lo, hi = TERMINATOR_BAND
    t = prev_metrics.get("terminators", 0)
    if not (lo <= t <= hi):
        lines.append(f"  * {t} terminators. Use between {lo} and {hi}, sharing one exception "
                     f"terminator across several failed branches.")
    return "\n".join(lines) + "\n\n"


def generate_process_mermaid(proc, data, attempt=0, prev_metrics=None,
                             prev_degenerate=None):
    """Call 2 — raw Mermaid only, so no \\n survives a JSON string round trip."""
    backend = backend_for(proc["l1"])
    steps = "\n".join(
        f"  {s.get('step','')} {s.get('name','')} "
        f"[role: {s.get('role','')} | system: {s.get('system','')} | "
        f"decision: {s.get('decision_point','N')} | exception: {s.get('exception','N')}]"
        for s in data.get("l4_steps", [])
    )
    regs = registry_regs_for(proc["l1"])
    reg_hint = ", ".join(r["citation"] for r in regs[:6]) or "none specific"
    user = (
        f"{repair_directive(prev_metrics, prev_degenerate)}"
        f"Draw the BPMN process flow for {proc['pid']} — {proc['name']}\n"
        f"in the {proc['l1_name']} domain of a mobility platform.\n\n"
        f"{archetype_directive(proc)}\n"
        f"These are the L4 steps it must cover:\n{steps}\n\n"
        "STRUCTURE — copy this construct exactly. It is from a different industry, so take\n"
        "the FORM and none of the content:\n\n"
        f"{BPMN_FORM_EXAMPLE}\n\n"
        f"{BPMN_ANTIPATTERN}\n\n"
        "REQUIREMENTS:\n"
        "- flowchart LR with 5 or 6 phase subgraphs named P1 to P6, each titled\n"
        "  Phase N: short phase name.\n"
        "- One ([Start]) terminator and at least one exception terminator such as\n"
        "  ([Reject]), ([Hold]), ([Escalate]) or ([Suspend]), plus an ([End]).\n"
        "- 5 to 8 decision diamonds using curly braces. EVERY decision has at least two\n"
        "  labelled outbound branches written as X -- Yes --> Y and X -- No --> Z.\n"
        "  Use real mobility decision language appropriate to this domain, for example:\n"
        "  background check cleared, disengagement triggered, BVLOS waiver approved,\n"
        "  redistribution threshold hit, surge cap breached, merchant accepted in time,\n"
        "  conformity finding raised, geofence violation detected, fleet cap exceeded.\n"
        "  Every decision must name a THRESHOLD or a BUSINESS CONDITION. Never write a\n"
        "  decision that only asks whether the previous step succeeded.\n"
        "- MANDATORY: at least 2 rework loops. A rework loop means a failed decision\n"
        "  points BACK to a task node that appears EARLIER in the flow, forming a cycle,\n"
        "  as in QUAL -- No --> BACKFILL followed by BACKFILL --> ING. A diagram with no\n"
        "  cycle is rejected no matter how many nodes it has. Routing a No branch to an\n"
        "  exception terminator does NOT count as a rework loop.\n"
        "- At MOST 3 terminators in total, including ([Start]) and ([End]). Several failed\n"
        "  branches should SHARE one exception terminator. Do not create one per decision.\n"
        "- 22 to 30 nodes overall. Every task label is two lines: what happens, then a\n"
        "  literal backslash-n, then the system or document involved.\n"
        "  The line break is a SINGLE backslash followed by n. Not two backslashes.\n"
        "  Example: VER[Verify parking photo at end of ride\\nMDS feed and operator console]\n"
        "  Name each system ONCE in a label. Never repeat the vendor after the product,\n"
        "  as in 'Joyride Fleet Management Dashboard Joyride'.\n"
        "- Flow must cross subgraph boundaries: a node in P2 connects to nodes in P3 and,\n"
        "  where there is rework, back to P1.\n"
        "- Close with at least 8 style lines. Terminators fill:#0f2a5c,color:#fff,stroke:#0f2a5c\n"
        "  and every decision diamond fill:#10b3c6,color:#fff,stroke:#10b3c6.\n"
        f"- Where a regulation is named in a label use only these: {reg_hint}\n"
        "- Node IDs start with a letter. No parentheses, ampersands or angle brackets inside\n"
        "  any label. Never use <br/>. Arrows are --> only.\n\n"
        "Output the raw Mermaid and nothing else. No JSON, no fences, no commentary.\n"
    )
    model = model_ladder(backend, attempt)
    try:
        raw = call_model(SYSTEM_PROMPT_MMD, user, backend,
                         temperature=0.2 + 0.1 * attempt, model=model)
        return sanitise_mermaid(fix_breaks(raw))
    except Exception as exc:
        log(f"{proc['pid']}: mermaid call failed on {model} — {exc}", "WARN")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TOLERANT JSON EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_json(raw, required=None):
    """Find the first balanced object that parses AND carries the expected keys.

    Small models often prepend a Mermaid block; its %%{init: {...}}%% braces are
    the first thing a naive scanner finds, so those are stripped before scanning
    and every remaining candidate is tried in turn.
    """
    if not raw:
        return None
    text = re.sub(r'^```[a-z]*\n?', '', raw.strip(), flags=re.MULTILINE)
    text = re.sub(r'```$', '', text, flags=re.MULTILINE)
    text = re.sub(r'%%\{.*?\}%%', '', text, flags=re.DOTALL)          # mermaid init
    text = re.sub(r'^\s*(flowchart|graph)\s+\w+.*$', '', text, flags=re.MULTILINE)

    def candidates(s):
        depth = start = 0
        in_str = esc = False
        for i, ch in enumerate(s):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                if depth:
                    depth -= 1
                    if depth == 0:
                        yield s[start:i + 1]

    best = None
    for blob in candidates(text):
        for attempt in (blob, blob.replace("\n", " "), re.sub(r',\s*([}\]])', r'\1', blob)):
            try:
                data = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                break
            if required and not any(data.get(k) for k in required):
                best = best or data
                break
            return data
    return best


# ─────────────────────────────────────────────────────────────────────────────
# RICHNESS SCORING — floors measured from the sibling repos' own diagrams.
#   airline .mmd (n=149): median 30 nodes, 6 decisions, 12 branches, 5 subgraphs,
#                         8 style lines, 2 terminators
#   shipping .svg (n=16): median 49 node groups, 13 clusters, 49 edge labels
# ─────────────────────────────────────────────────────────────────────────────

# Scored metrics — each contributes one point.
PID_FLOOR = {"nodes": 30, "decisions": 6, "branches": 12, "subgraphs": 5,
             "styles": 8, "terminators": 2}

# HARD GATES — a draft that misses one of these fails regardless of its score.
#
# loops: the difference between a real BPMN flow and a linear checklist with dead
#   ends bolted on, so not tradeable against node count. Airline reference
#   (n=149): median 4 back-edges, 139/149 carry >= 2.
#
# substantive_decisions: a decision that only asks whether the previous step
#   worked ("Ingestion successful?", "Aggregation complete?") is error handling,
#   not a business decision. Telling the model this in prose did not work — the
#   second draft of MM-MD-DM-01 still produced 9 of them and 0 real ones — so it
#   is enforced structurally. Airline reference median is 3.
PID_GATES = {"loops": 2, "substantive_decisions": 3}

# A decision is DEGENERATE if it merely asks whether the prior step succeeded.
_DEGENERATE_DECISION = re.compile(
    r'\b(?:success(?:ful)?|complete[d]?|collected|received|generated|created|'
    r'recognis?z?ed|analys?z?ed|executed|finished|done|made|performed|'
    r'processed|ingested|available|valid|ok)\b\s*\??\s*$', re.IGNORECASE)

# A decision is SUBSTANTIVE if it names a threshold, a comparator or a real
# domain condition.
_SUBSTANTIVE_DECISION = re.compile(
    r'\d|\b(?:above|below|within|under|over|exceed\w*|breach\w*|threshold|cap|caps|'
    r'tolerance|limit|minimum|maximum|percent|sla|band|margin|budget|'
    r'approved|cleared|granted|waiver|permit|eligible|compliant|conforming|'
    r'triggered|detected|raised|flagged|violat\w*|met|missed|expired|overdue|'
    r'greater|less|more than|at least)\b', re.IGNORECASE)


def classify_decisions(mmd):
    """Split decision diamonds into (substantive, degenerate) label lists."""
    subs, degs = [], []
    for raw in re.findall(r'[A-Za-z][A-Za-z0-9_]*\{([^}]+)\}', mmd):
        clean = raw.replace('\\n', ' ').strip()
        if _SUBSTANTIVE_DECISION.search(clean) and not _DEGENERATE_DECISION.search(clean):
            subs.append(clean)
        else:
            degs.append(clean)
    return subs, degs

# Terminators are scored as a BAND, not a floor. The first generated draft of
# MM-MD-DM-01 scored a point for 9 terminators — every "No" branch dead-ended in
# its own ([Exception]) node, which is the anti-pattern, not richness.
TERMINATOR_BAND = (2, 6)

EA_FLOOR = {"nodes": 22, "labelled": 12, "subgraphs": 5, "classdefs": 5}


def _node_ids(mmd):
    ids = set(re.findall(r'([A-Za-z][A-Za-z0-9_]*)\s*(?:\[|\{|\(\[)', mmd))
    return ids - {"subgraph", "flowchart", "graph", "classDef", "style",
                  "class", "direction", "end"}


def parse_edges(mmd):
    """Every A --> B edge, in all four mermaid arrow forms:
    A --> B  /  A -- label --> B  /  A -->|label| B  /  A[x] --> B[y]"""
    body = re.sub(r'^\s*(?:classDef|style|class)\s.*$', '', mmd, flags=re.MULTILINE)
    pat = re.compile(
        r'([A-Za-z][A-Za-z0-9_]*)'
        r'(?:\s*(?:\[[^\]]*\]|\{[^}]*\}|\(\[[^\]]*\]\)|\([^)]*\)))?'
        r'\s*(?:--\s*[^->|\n]*?\s*)?-->'
        r'(?:\s*\|[^|\n]*\|)?'
        r'\s*([A-Za-z][A-Za-z0-9_]*)')
    edges = []
    for line in body.split('\n'):
        pos = 0
        while True:
            m = pat.search(line, pos)
            if not m:
                break
            edges.append((m.group(1), m.group(2)))
            pos = m.start(2)                      # allow A --> B --> C chains
    return edges


def count_rework_loops(mmd):
    """A rework loop is a CYCLE in the flow graph — a failed decision routed back
    to earlier work. A dead-end ([Exception]) terminator creates no cycle, which
    is exactly the distinction we need.

    The previous implementation compared first-appearance order and indexed only
    nodes declared at the start of a line. In practice most nodes are declared
    mid-line as an arrow target, so the index was nearly empty and it reported
    zero loops on all 149 airline reference diagrams, which visibly contain them.
    """
    adj = {}
    for src, dst in parse_edges(mmd):
        adj.setdefault(src, []).append(dst)
        adj.setdefault(dst, [])
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in adj}
    back = 0

    def dfs(root):
        nonlocal back
        stack = [(root, iter(adj[root]))]
        colour[root] = GREY
        while stack:
            node, it = stack[-1]
            for nxt in it:
                if colour[nxt] == GREY:
                    back += 1
                elif colour[nxt] == WHITE:
                    colour[nxt] = GREY
                    stack.append((nxt, iter(adj[nxt])))
                    break
            else:
                colour[node] = BLACK
                stack.pop()

    for n in list(adj):
        if colour[n] == WHITE:
            dfs(n)
    return back


def diagram_richness(mmd):
    """Returns (score, metrics, gate_failures). A non-empty gate_failures list
    means the draft is unacceptable however high the score."""
    if not mmd:
        return 0, {}, list(PID_GATES)
    m = {
        "nodes":       len(_node_ids(mmd)),
        "decisions":   len(set(re.findall(r'([A-Za-z][A-Za-z0-9_]*)\{[^}]+\}', mmd))),
        # Count UNIQUE labelled branches. Counting raw occurrences let a model
        # inflate the score by restating every edge after the subgraphs.
        "branches":    len({(s, d) for s, d in parse_edges(mmd)}),
        "subgraphs":   mmd.count("subgraph"),
        "styles":      len(re.findall(r'^\s*style\s', mmd, flags=re.MULTILINE)),
        "terminators": len(re.findall(r'\(\[', mmd)),
        "loops":       count_rework_loops(mmd),
        "substantive_decisions": len(classify_decisions(mmd)[0]),
    }
    score = 0
    for k, floor in PID_FLOOR.items():
        if k == "terminators":
            lo, hi = TERMINATOR_BAND
            if lo <= m[k] <= hi:
                score += 1
        elif m[k] >= floor:
            score += 1
    gate_failures = [k for k, need in PID_GATES.items() if m[k] < need]
    return score, m, gate_failures


def ea_richness(mmd):
    if not mmd:
        return 0, {}
    m = {
        "nodes":     len(_node_ids(mmd)),
        "labelled":  mmd.count("-->|"),
        "subgraphs": mmd.count("subgraph"),
        "classdefs": mmd.count("classDef"),
    }
    score = sum(1 for k, floor in EA_FLOOR.items() if m[k] >= floor)
    return score, m


# ─────────────────────────────────────────────────────────────────────────────
# MMDC RENDERING
# ─────────────────────────────────────────────────────────────────────────────

def render_mermaid(mmd_text, mmd_path, out_path, width, height, scale=MMDC_SCALE):
    mmd_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mmd_path.write_text(mmd_text, encoding="utf-8")
    is_svg = out_path.suffix.lower() == ".svg"
    cmd = ["mmdc", "-i", str(mmd_path), "-o", str(out_path),
           "-w", str(width), "-H", str(height), "--backgroundColor", "white"]
    if not is_svg:
        cmd += ["--scale", str(scale)]
    env = dict(os.environ)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
    except subprocess.TimeoutExpired:
        return False, "mmdc timed out"
    except FileNotFoundError:
        return False, "mmdc not found on PATH"
    if res.returncode != 0:
        return False, (res.stderr or res.stdout or "mmdc failed").strip()[:400]
    floor = 1024 if is_svg else 4096
    if not out_path.exists() or out_path.stat().st_size < floor:
        return False, f"mmdc produced no usable {out_path.suffix.lstrip('.')}"
    size_mb = out_path.stat().st_size / (1024 * 1024)
    if not is_svg and size_mb > 90 and scale > 1:
        log(f"{out_path.name}: {size_mb:.1f}MB — re-rendering at lower scale", "WARN")
        return render_mermaid(mmd_text, mmd_path, out_path, int(width * 0.75),
                              int(height * 0.75), scale=scale - 1)
    return True, f"{size_mb:.2f}MB"


def finalize_svg(path):
    """mmdc emits width="100%" plus an inline max-width on the root <svg>.

    Both are hostile to zooming: the max-width caps how large the vector will
    ever render, so the browser rasterises at that ceiling and scales the bitmap
    up — which looks exactly like a blurry PNG. Replacing them with the viewBox
    dimensions gives the file a real intrinsic size and no ceiling.

    Every OTHER max-width in the file is stripped too. The remainder are the dead
    div.mermaidTooltip rule (there are no tooltips in a static <img>) and the
    foreignObject label divs, which also carry white-space:nowrap and are
    therefore unaffected. This makes `grep -c 'max-width'` return 0.
    """
    try:
        svg = path.read_text(encoding="utf-8")
    except Exception:
        return False
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    if not m:
        return False
    w, h = m.group(1), m.group(2)
    svg = svg.replace('width="100%"', f'width="{w}" height="{h}"', 1)
    svg = re.sub(r'max-width:\s*[\d.]+px;?\s*', '', svg)          # ALL of them
    svg = re.sub(r'max-width:\s*[^;"}]+;?\s*', '', svg)           # any non-px form
    if 'height=' not in svg.split('>', 1)[0]:
        svg = svg.replace('<svg ', f'<svg height="{h}" ', 1)
    # Belt and braces on the font. The init block sets it, but mermaid also emits
    # a --mermaid-font-family custom property and may quote the family name, so
    # every remaining default declaration is rewritten here regardless of form.
    svg = re.sub(r'"?trebuchet ms"?\s*,\s*verdana\s*,\s*arial\s*,\s*sans-serif',
                 FONT_STACK, svg, flags=re.IGNORECASE)
    path.write_text(svg, encoding="utf-8")
    residual = svg.count("max-width")
    log(f"  svg finalised — intrinsic {w}x{h}, max-width occurrences remaining: {residual}")
    return residual == 0


def build_diagram(proc, data):
    """Generate, score, sanitise and render. Up to 3 drafts; publish the best.

    A draft that fails a hard gate (rework loops) is never accepted early, no
    matter how well it scores elsewhere — all three drafts are spent trying to
    get a real one.
    """
    mmd_path = DIAGRAM_DIR / f"{proc['slug']}.mmd"
    svg_path = IMG_DIR / f"{proc['slug']}.svg"
    best, best_key, best_metrics, best_gates = None, (-99, -1), {}, list(PID_GATES)
    prev_metrics, prev_degenerate = None, None

    for attempt in range(3):
        candidate = generate_process_mermaid(proc, data, attempt=attempt,
                                             prev_metrics=prev_metrics,
                                             prev_degenerate=prev_degenerate)
        score, metrics, gates = diagram_richness(candidate)
        # Rank by FEWEST gate failures first, then score. A draft that clears every
        # gate always beats a higher-scoring one that does not.
        key = (-len(gates), score)
        if candidate and key > best_key:
            best, best_key, best_metrics, best_gates = candidate, key, metrics, gates
        # Carry this draft's specific failures into the next attempt.
        prev_metrics = metrics if candidate else None
        prev_degenerate = classify_decisions(candidate)[1] if candidate else None
        gate_note = f" GATE FAIL: {', '.join(gates)}" if gates else " gates ok"
        log(f"  diagram draft {attempt+1}: score {score}/{len(PID_FLOOR)}{gate_note} {metrics}")
        if candidate and "substantive_decisions" in gates:
            _, degs = classify_decisions(candidate)
            log(f"    degenerate decisions ({len(degs)}): "
                f"{'; '.join(degs[:4])}", "WARN")
        if not gates and score >= len(PID_FLOOR) - 1:
            break

    if not best:
        return None
    if best_gates:
        log(f"  {proc['pid']}: REJECTED BY GATE after 3 drafts — "
            f"{', '.join(f'{g} < {PID_GATES[g]}' for g in best_gates)}. "
            f"A flow with no rework loop is a linear checklist, not a process. "
            f"Publishing the best draft anyway; re-run with "
            f"--pid {proc['pid']} --force to try again", "WARN")
    elif best_key[1] < len(PID_FLOOR) - 2:
        short = [k for k, f in PID_FLOOR.items() if best_metrics.get(k, 0) < f]
        log(f"  {proc['pid']}: diagram UNDER FLOOR (score {best_key[1]}/{len(PID_FLOOR)}, "
            f"short on {', '.join(short)}) — publishing anyway", "WARN")

    for attempt in range(1, 4):
        ok, info = render_mermaid(best, mmd_path, svg_path, PID_W, PID_H)
        if ok:
            finalize_svg(svg_path)
            log(f"  diagram rendered as SVG ({info}) on render attempt {attempt}")
            return svg_path
        log(f"  mmdc attempt {attempt}/3 failed: {info}", "WARN")
        retry = generate_process_mermaid(proc, data, attempt=attempt)
        if retry:
            best = retry
    return None


# ─────────────────────────────────────────────────────────────────────────────
# GITHUB
# ─────────────────────────────────────────────────────────────────────────────

def _make_session():
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=2, status_forcelist=[500, 502, 503, 504],
                  allowed_methods=["GET", "PUT", "POST"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


GH_SESSION = _make_session()


def gh_headers():
    if not GITHUB_TOKEN:
        sys.exit("GITHUB_TOKEN is not set. Run: export GITHUB_TOKEN=$(gh auth token)")
    return {"Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def gh_get_sha(repo_path):
    try:
        r = GH_SESSION.get(f"{GH_API}/{repo_path}", headers=gh_headers(),
                           params={"ref": BRANCH}, timeout=60)
        if r.status_code == 200:
            return r.json().get("sha")
    except Exception:
        pass
    return None


def gh_push_file(repo_path, content, message=None):
    """Push text or bytes. 4 attempts at 2/4/8/16s. SHA fetched before every PUT."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    payload_b64 = b64encode(content).decode("ascii")
    msg = message or f"Update {repo_path}"
    for attempt in range(1, 5):
        try:
            body = {"message": msg, "content": payload_b64, "branch": BRANCH}
            sha = gh_get_sha(repo_path)
            if sha:
                body["sha"] = sha
            r = GH_SESSION.put(f"{GH_API}/{repo_path}", headers=gh_headers(),
                               json=body, timeout=120)
            if r.status_code in (200, 201):
                return True
            log(f"  push {repo_path} → HTTP {r.status_code} {r.text[:180]}", "WARN")
        except Exception as exc:
            log(f"  push {repo_path} error: {exc}", "WARN")
        time.sleep(2 ** attempt)
    log(f"  GAVE UP pushing {repo_path}", "ERROR")
    return False


def push_deploy():
    """Always last — it is what triggers the Pages rebuild."""
    stamp = datetime.now().isoformat(timespec="seconds")
    ok = gh_push_file(".deploy", f"deploy {stamp}\n", f"Deploy {stamp}")
    log("`.deploy` pushed — Pages rebuild triggered" if ok else "`.deploy` push failed",
        "INFO" if ok else "ERROR")
    return ok


def verify_live(url, wait=VERIFY_WAIT, needle="assets/img"):
    log(f"  waiting {wait}s for Pages build …")
    time.sleep(wait)
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=45)
            if r.status_code == 200 and needle in r.text:
                return True
            log(f"  verify attempt {attempt+1}: HTTP {r.status_code}", "WARN")
        except Exception as exc:
            log(f"  verify attempt {attempt+1} error: {exc}", "WARN")
        time.sleep(20)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# LOCAL TRACKER  (never pushed)
# ─────────────────────────────────────────────────────────────────────────────

def load_tracker():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if TRACKER.exists():
        try:
            return json.loads(TRACKER.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log("processes.json unreadable — starting a fresh tracker", "WARN")
    return {}


# One lock guards the tracker dict and its file. With --parallel several worker
# threads finish at once, and an unguarded read-modify-write would lose entries
# or leave truncated JSON on disk.
TRACKER_LOCK = threading.Lock()


def save_tracker(tr):
    """Atomic write: a crash mid-write must not leave an unparseable tracker."""
    tmp = TRACKER.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(tr, indent=2), encoding="utf-8")
    tmp.replace(TRACKER)


def is_complete(pid, tr):
    return tr.get(pid, {}).get("status") == "Complete"


def mark_complete(pid, tr, url, validation=None):
    entry = {"status": "Complete", "url": url,
             "template_version": TEMPLATE_VERSION,
             "completed_at": datetime.now().isoformat(timespec="seconds")}
    if validation:
        entry["validation"] = validation
    with TRACKER_LOCK:
        tr[pid] = entry
        save_tracker(tr)


# ─────────────────────────────────────────────────────────────────────────────
# HTML HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def esc(text):
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def prefix(depth):
    return "../" * depth


def trunc(text, n=52):
    t = str(text or "")
    return t if len(t) <= n else t[:n - 1] + "…"


def sys_tag_class(name):
    n = str(name or "").lower()
    if any(k in n for k in ("faa", "cpuc", "dmv", "mds", "gbfs", "astm", "part ")):
        return "sys-reg"
    if any(k in n for k in ("michelangelo", "deepeta", "h3", "ray", "kafka", "kubernetes")):
        return "sys-platform"
    if any(k in n for k in ("populus", "lacuna", "ride report", "joyride", "blue systems")):
        return "sys-city"
    return "sys-other"


def sys_tags(systems):
    if not systems:
        return '<span class="text-muted">None captured</span>'
    return " ".join(f'<span class="sys-tag {sys_tag_class(s)}">{esc(s)}</span>'
                    for s in systems)


def confidence_badge(level):
    lvl = str(level or "partial").lower()
    if "sparse" in lvl:
        return ('<span class="conf-badge conf-sparse" title="Public sourcing for this area is '
                'genuinely thin. Detail is deliberately limited rather than invented.">'
                'Sparse sourcing</span>')
    if "solid" in lvl:
        return '<span class="conf-badge conf-solid">Well sourced</span>'
    return '<span class="conf-badge conf-partial">Partially sourced</span>'


# ── Sidebar ─────────────────────────────────────────────────────────────────

def group_processes(l1_code, l2_code):
    return [p for p in PROCESSES if p["l1"] == l1_code and p["l2"] == l2_code]


def build_sidebar(depth, active_pid=None, active_ea=None):
    p = prefix(depth)
    out = ['<div class="nav-scroll">']
    for tier in (1, 2, 3):
        out.append(f'  <div class="nav-tier">{esc(TIER_LABEL[tier])}</div>')
        for code, (icon, name, slug, t) in L1_META.items():
            if t != tier:
                continue
            l2s = [(l1, l2, l2n, l2s_) for (l1, l2, l2n, l2s_, _) in TAXONOMY if l1 == code]
            is_open = active_pid and BY_PID.get(active_pid, {}).get("l1") == code
            out.append(f'  <div class="nav-domain{" open" if is_open else ""}">')
            out.append(f'    <a class="nav-l1" href="{p}{slug}/index.html">'
                       f'<span class="nav-ico">{icon}</span>{esc(name)}'
                       f'<span class="nav-count">{sum(1 for x in PROCESSES if x["l1"] == code)}</span></a>')
            out.append('    <div class="nav-l2-list">')
            for l1, l2, l2n, l2s_ in l2s:
                procs = group_processes(l1, l2)
                grp_open = active_pid and BY_PID.get(active_pid, {}).get("l2") == l2 \
                    and BY_PID.get(active_pid, {}).get("l1") == l1
                out.append(f'      <div class="nav-l2-group{" open" if grp_open else ""}">')
                out.append(f'        <a class="nav-l2-title" href="{p}{slug}/{l2s_}/index.html">'
                           f'{esc(l2n)}</a>')
                out.append('        <div class="nav-l3-list">')
                for pr in procs:
                    act = " active" if pr["pid"] == active_pid else ""
                    out.append(f'          <a class="nav-l3{act}" href="{p}{pr["path"]}" '
                               f'title="{esc(pr["name"])}">{pr["pid"]} {esc(trunc(pr["name"], 40))}</a>')
                out.append('        </div></div>')
            out.append('    </div></div>')
    ea_act = " open" if active_ea else ""
    out.append(f'  <div class="nav-tier">Enterprise Architecture</div>')
    out.append(f'  <div class="nav-domain{ea_act}">')
    out.append(f'    <a class="nav-l1" href="{p}{EA_DIR_SLUG}/index.html">'
               f'<span class="nav-ico">\U0001F5FA</span>EA Diagrams'
               f'<span class="nav-count">{len(EA_DIAGRAMS)}</span></a>')
    out.append('    <div class="nav-l2-list"><div class="nav-l2-group open"><div class="nav-l3-list">')
    for ea_id, title, _ in EA_DIAGRAMS:
        act = " active" if ea_id == active_ea else ""
        out.append(f'      <a class="nav-l3{act}" href="{p}{EA_DIR_SLUG}/{ea_id}/index.html">'
                   f'{ea_id.upper()} {esc(trunc(title, 34))}</a>')
    out.append('    </div></div></div></div>')
    out.append('</div>')
    return "\n".join(out)


def page_shell(title, topbar_sub, depth, main_html, active_pid=None, active_ea=None):
    p = prefix(depth)
    return f"""<!DOCTYPE html>
<!-- mobility-wiki template v{TEMPLATE_VERSION} -->
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="generator" content="mobility-wiki template v{TEMPLATE_VERSION}">
  <title>{title} &mdash; Mobility Process Wiki</title>
  <link rel="stylesheet" href="{p}assets/css/wiki.css">
</head>
<body>
  <div class="topbar">
    <button id="topbarToggle" aria-label="Menu"><span></span><span></span><span></span></button>
    <a class="topbar-brand" href="{p}index.html">{SITE_TITLE}</a>
    <span class="topbar-sub">{topbar_sub}</span>
    <span class="topbar-spacer"></span>
  </div>
  <div class="wiki-layout">
    <nav id="sidebar">
      <button id="sidebarToggle" title="Collapse sidebar">&#9664;</button>
{build_sidebar(depth, active_pid, active_ea)}
    </nav>
    <main class="wiki-main">
{main_html}
      <footer class="wiki-footer">
        <p>{DISCLAIMER}</p>
        <p class="footer-meta">Generated {datetime.now().strftime('%Y-%m-%d')}
           &bull; template v{TEMPLATE_VERSION}</p>
      </footer>
    </main>
  </div>
  <div id="lightbox"><img id="lightboxImg" src="" alt=""></div>
  <script src="{p}assets/js/wiki.js"></script>
</body>
</html>
"""


# ── Process page ────────────────────────────────────────────────────────────

def build_process_page(proc, data):
    p = prefix(DEPTH_PROCESS)
    rows = []
    for s in data.get("l4_steps", []):
        dec = ('<span class="decision-y">Y</span>'
               if str(s.get("decision_point", "N")).upper().startswith("Y") else "N")
        exc = ('<span class="exception-y">Y</span>'
               if str(s.get("exception", "N")).upper().startswith("Y") else "N")
        rows.append(f"""        <tr>
          <td class="step-num">{esc(s.get('step',''))}</td>
          <td>{esc(s.get('name',''))}</td>
          <td>{esc(s.get('role',''))}</td>
          <td><span class="sys-tag {sys_tag_class(s.get('system'))}">{esc(s.get('system',''))}</span></td>
          <td>{esc(s.get('input',''))}</td>
          <td>{esc(s.get('output',''))}</td>
          <td>{esc(s.get('kpi',''))}</td>
          <td>{esc(s.get('pain_point',''))}</td>
          <td>{dec}</td>
          <td>{exc}</td>
        </tr>""")

    kpis = " ".join(f'<span class="kpi-pill">{esc(k)}</span>' for k in data.get("kpis", []))
    risks = " ".join(f'<span class="risk-pill">{esc(r)}</span>' for r in data.get("risks", []))
    lanes = " ".join(
        f'<span class="lane-pill">{esc(l.get("role",""))} &middot; '
        f'{esc(", ".join(str(x) for x in l.get("steps", [])))}</span>'
        for l in data.get("swim_lanes", []) if isinstance(l, dict))

    conf = data.get("sourcing_confidence", "partial")
    arch_note = data.get("archetype_notes", "")

    main = f"""      <div class="page-header">
        <div class="breadcrumb">
          <a href="{p}index.html">Home</a> &rsaquo;
          <a href="{p}{proc['l1_slug']}/index.html">{esc(proc['l1_name'])}</a> &rsaquo;
          <a href="{p}{proc['l1_slug']}/{proc['l2_slug']}/index.html">{esc(proc['l2_name'])}</a>
        </div>
        <h1>
          <span class="pid-badge tier-{proc['tier']}">{proc['l1']}</span>
          {proc['pid']} &mdash; {esc(proc['name'])}
        </h1>
        <p>{esc(data.get('description',''))}</p>
        <p class="badge-row">{confidence_badge(conf)}
           <span class="tier-badge">{esc(TIER_LABEL[proc['tier']])}</span></p>
      </div>

      <div class="card">
        <div class="card-header">&#x1F5FA; BPMN Process Flow</div>
        <div class="card-body">
          <div class="diagram-wrap">
            <a href="{p}assets/img/{proc['slug']}.svg" data-lightbox data-title="{proc['pid']} BPMN">
              <img src="{p}assets/img/{proc['slug']}.svg" alt="{proc['pid']} BPMN Diagram">
            </a>
            <p>Vector diagram &mdash; stays sharp at any zoom &bull; Click to zoom &bull;
               Scroll to zoom &bull; Drag to pan &bull;
               <a href="{p}assets/img/{proc['slug']}.svg" download>Download SVG</a></p>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">&#x1F4CB; Process Attributes</div>
        <div class="card-body">
          <table class="attr-table">
            <tr><th>Process ID</th><td>{proc['pid']}</td></tr>
            <tr><th>Tier</th><td>{esc(TIER_LABEL[proc['tier']])}</td></tr>
            <tr><th>L1 Domain</th><td>{proc['l1_icon']} {esc(proc['l1_name'])}</td></tr>
            <tr><th>L2 Process Group</th><td>{esc(proc['l2_name'])}</td></tr>
            <tr><th>L3 Name</th><td>{esc(proc['name'])}</td></tr>
            <tr><th>Trigger</th><td>{esc(data.get('trigger',''))}</td></tr>
            <tr><th>Outcome</th><td>{esc(data.get('outcome',''))}</td></tr>
            <tr><th>Archetype Variation</th><td>{esc(arch_note) or '<span class="text-muted">Not captured</span>'}</td></tr>
            <tr><th>Systems</th><td>{sys_tags(data.get('systems'))}</td></tr>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">&#x1F4CB; L4 Process Steps</div>
        <div class="card-body">
          <div class="l4-table-wrap">
            <table class="l4-table">
              <thead>
                <tr>
                  <th>Step</th><th>Name</th><th>Role</th><th>System</th>
                  <th>Input</th><th>Output</th><th>KPI</th><th>Pain Point / Risk</th>
                  <th>Decision?</th><th>Exception?</th>
                </tr>
              </thead>
              <tbody>
{chr(10).join(rows)}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">&#x1F4CA; KPIs &amp; Risk Register</div>
        <div class="card-body">
          <p class="mb-8"><strong>KPIs</strong></p>
          <div class="kpi-list mb-8">{kpis or '<span class="text-muted">None captured</span>'}</div>
          <p class="mb-8 mt-16"><strong>Key Risks</strong></p>
          <div class="kpi-list">{risks or '<span class="text-muted">None captured</span>'}</div>
          {'<p class="mb-8 mt-16"><strong>Swim Lanes</strong></p><div class="kpi-list">' + lanes + '</div>' if lanes else ''}
        </div>
      </div>
"""
    return page_shell(f"{proc['pid']} &mdash; {esc(proc['name'])}",
                      f"{esc(proc['l1_name'])} &rsaquo; {esc(proc['l2_name'])}",
                      DEPTH_PROCESS, main, active_pid=proc["pid"])


# ── Index pages ─────────────────────────────────────────────────────────────

def status_cell(pid, tr):
    return ('<span class="st-done">Complete</span>' if is_complete(pid, tr)
            else '<span class="st-todo">Planned</span>')


def build_l2_index(l1_code, l2_code, tr):
    icon, l1_name, l1_slug, tier = L1_META[l1_code]
    l2_name = next(t[2] for t in TAXONOMY if t[0] == l1_code and t[1] == l2_code)
    procs = group_processes(l1_code, l2_code)
    p = prefix(DEPTH_L2)
    rows = "\n".join(
        f'        <tr><td class="step-num">{pr["pid"]}</td>'
        f'<td><a href="{pr["pid"].lower()}/index.html">{esc(pr["name"])}</a></td>'
        f'<td>{status_cell(pr["pid"], tr)}</td></tr>' for pr in procs)
    main = f"""      <div class="page-header">
        <div class="breadcrumb">
          <a href="{p}index.html">Home</a> &rsaquo;
          <a href="../index.html">{esc(l1_name)}</a>
        </div>
        <h1>{icon} {esc(l2_name)}</h1>
        <p>{len(procs)} processes in {esc(l1_name)}.</p>
      </div>
      <div class="card"><div class="card-body">
        <table class="attr-table wide">
          <thead><tr><th>PID</th><th>Process</th><th>Status</th></tr></thead>
          <tbody>
{rows}
          </tbody>
        </table>
      </div></div>
"""
    return page_shell(esc(l2_name), esc(l1_name), DEPTH_L2, main)


def build_l1_index(l1_code, tr):
    icon, l1_name, l1_slug, tier = L1_META[l1_code]
    p = prefix(DEPTH_L1)
    cards = []
    for l1, l2, l2n, l2s_, names in TAXONOMY:
        if l1 != l1_code:
            continue
        done = sum(1 for pr in group_processes(l1, l2) if is_complete(pr["pid"], tr))
        cards.append(f"""    <div class="ea-card">
      <h4><a href="{l2s_}/index.html">{esc(l2n)}</a></h4>
      <p>{len(names)} processes &bull; {done} complete</p>
    </div>""")
    total = sum(1 for x in PROCESSES if x["l1"] == l1_code)
    main = f"""      <div class="page-header">
        <div class="breadcrumb"><a href="{p}index.html">Home</a></div>
        <h1>{icon} {esc(l1_name)}</h1>
        <p>{esc(TIER_LABEL[tier])} &bull; {total} processes across
           {len(cards)} process groups.</p>
      </div>
      <div class="ea-grid">
{chr(10).join(cards)}
      </div>
"""
    return page_shell(esc(l1_name), esc(TIER_LABEL[tier]), DEPTH_L1, main)


def build_home(tr):
    done = sum(1 for pr in PROCESSES if is_complete(pr["pid"], tr))
    sections = []
    for tier in (1, 2, 3):
        cards = []
        for code, (icon, name, slug, t) in L1_META.items():
            if t != tier:
                continue
            n = sum(1 for x in PROCESSES if x["l1"] == code)
            d = sum(1 for x in PROCESSES if x["l1"] == code and is_complete(x["pid"], tr))
            cards.append(f"""    <div class="ea-card tier-{tier}">
      <h4><a href="{slug}/index.html">{icon} {esc(name)}</a></h4>
      <p>{n} processes &bull; {d} complete</p>
    </div>""")
        sections.append(f'      <h2 class="tier-heading tier-h{tier}">{esc(TIER_LABEL[tier])}</h2>\n'
                        f'      <div class="ea-grid">\n{chr(10).join(cards)}\n      </div>')
    main = f"""      <div class="page-header">
        <h1>{SITE_TITLE}</h1>
        <p>{SITE_SUB}</p>
        <p>A homogeneous process taxonomy spanning six mobility operating models that share a
           marketplace and dispatch core: ride-hail, autonomous ride-hail, last-mile delivery,
           micromobility, eVTOL air mobility and drone delivery.
           <strong>{len(PROCESSES)} processes</strong> across
           <strong>{len(L1_META)} domains</strong> and {len(TAXONOMY)} process groups
           &bull; {done} complete.</p>
      </div>
      <div class="card"><div class="card-body">
        <p><strong>On sourcing.</strong> Every process is grounded against a registry of
        researched, verified facts. Where public sourcing is genuinely thin &mdash; Waymo's
        production autonomy stack, eVTOL operational procedure, drone operators' internal
        orchestration &mdash; pages are marked
        {confidence_badge('sparse')} and detail is deliberately limited rather than invented.</p>
      </div></div>
{chr(10).join(sections)}
"""
    return page_shell("Home", "Process Catalogue", 0, main)


def build_ea_index():
    cards = []
    for ea_id, title, scope in EA_DIAGRAMS:
        cards.append(f"""    <div class="ea-card">
      <h4><a href="{ea_id}/index.html">{ea_id.upper()} &mdash; {esc(title)}</a></h4>
      <p>{esc(scope)}</p>
    </div>""")
    main = f"""      <div class="page-header">
        <div class="breadcrumb"><a href="{prefix(DEPTH_EA_IDX)}index.html">Home</a></div>
        <h1>&#x1F5FA; Enterprise Architecture</h1>
        <p>System landscape and data flow diagrams across the mobility estate.
           Every diagram renders at 4K as a vector &mdash; click to zoom.</p>
      </div>
      <div class="ea-grid">
{chr(10).join(cards)}
      </div>
"""
    return page_shell("Enterprise Architecture", "Enterprise Architecture",
                      DEPTH_EA_IDX, main, active_ea="index")


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ─────────────────────────────────────────────────────────────────────────────

def push_shell(tr):
    ok = True
    ok &= gh_push_file(".nojekyll", "", "Disable Jekyll processing")
    css = (ROOT / "assets" / "css" / "wiki.css").read_text(encoding="utf-8")
    js = (ROOT / "assets" / "js" / "wiki.js").read_text(encoding="utf-8")
    ok &= gh_push_file("assets/css/wiki.css", css, "Add stylesheet")
    ok &= gh_push_file("assets/js/wiki.js", js, "Add lightbox and navigation")
    ok &= gh_push_file("index.html", build_home(tr), "Add home page")
    ok &= gh_push_file(f"{EA_DIR_SLUG}/index.html", build_ea_index(), "Add EA index")
    for code in L1_META:
        ok &= gh_push_file(f"{L1_META[code][2]}/index.html", build_l1_index(code, tr),
                           f"Add {code} index")
    for l1, l2, l2n, l2s_, _ in TAXONOMY:
        ok &= gh_push_file(f"{L1_META[l1][2]}/{l2s_}/index.html",
                           build_l2_index(l1, l2, tr), f"Add {l1}-{l2} index")
    return ok


def rebuild_nav(tr, deploy=True):
    gh_push_file("index.html", build_home(tr), "Rebuild home")
    gh_push_file(f"{EA_DIR_SLUG}/index.html", build_ea_index(), "Rebuild EA index")
    for code in L1_META:
        gh_push_file(f"{L1_META[code][2]}/index.html", build_l1_index(code, tr),
                     f"Rebuild {code} index")
    for l1, l2, l2n, l2s_, _ in TAXONOMY:
        gh_push_file(f"{L1_META[l1][2]}/{l2s_}/index.html",
                     build_l2_index(l1, l2, tr), f"Rebuild {l1}-{l2} index")
    if deploy:
        push_deploy()


def process_one(proc, tr, tag=""):
    log(f"──{tag} {proc['pid']} — {proc['name']}  [backend: {backend_for(proc['l1'])}]")
    data = generate_process_content(proc)
    if not data:
        log(f"{proc['pid']}: no usable content JSON — skipped", "ERROR")
        return None
    validation = validate_process(proc, data)
    svg = build_diagram(proc, data)
    if not svg:
        log(f"{proc['pid']}: diagram failed after 3 attempts — skipped", "ERROR")
        return None
    if not gh_push_file(f"assets/img/{proc['slug']}.svg", svg.read_bytes(),
                        f"Add {proc['pid']} diagram"):
        return None
    if not gh_push_file(proc["path"], build_process_page(proc, data),
                        f"Add {proc['pid']} {proc['name']}"):
        return None
    url = f"{PAGES_BASE}/{proc['path']}"
    mark_complete(proc["pid"], tr, url, validation)
    log(f"  pushed {proc['pid']} → {url}")
    return url


def select_targets(args, tr):
    pool = PROCESSES
    if args.pid:
        want = args.pid.upper()
        if want not in BY_PID:
            sys.exit(f"Unknown PID {want}")
        return [BY_PID[want]]
    if args.start:
        want = args.start.upper()
        idx = next((i for i, p in enumerate(pool) if p["pid"] == want), None)
        if idx is None:
            sys.exit(f"Unknown PID {want}")
        pool = pool[idx:]
    if not args.force:
        pool = [p for p in pool if not is_complete(p["pid"], tr)]
    if args.full:
        return pool
    if args.count:
        return pool[:args.count]
    return pool[:1]


def main():
    ap = argparse.ArgumentParser(description="Mobility wiki generator")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--count", type=int)
    ap.add_argument("--pid")
    ap.add_argument("--start")
    ap.add_argument("--force", action="store_true",
                    help="regenerate even if the tracker marks it Complete")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--bootstrap", action="store_true")
    ap.add_argument("--rebuild-nav", action="store_true")
    ap.add_argument("-j", "--parallel", type=int, default=1, metavar="N",
                    help="run N processes concurrently (default 1). Each worker "
                         "holds an Ollama request and spawns its own headless "
                         "Chrome for mmdc, so N is bounded by RAM, not CPU.")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be generated, then exit")
    args = ap.parse_args()
    if args.parallel < 1:
        sys.exit("--parallel must be at least 1")

    for d in (DATA_DIR, DIAGRAM_DIR, IMG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    tr = load_tracker()

    if args.bootstrap:
        push_shell(tr)
        push_deploy()
        log("bootstrap complete")
        return
    if args.rebuild_nav:
        rebuild_nav(tr)
        log("nav rebuild complete")
        return

    targets = select_targets(args, tr)
    remaining = sum(1 for p in PROCESSES if not is_complete(p["pid"], tr))
    log(f"{len(targets)} process(es) selected "
        f"({remaining} of {len(PROCESSES)} still incomplete overall)")

    if args.dry_run:
        for i, p in enumerate(targets, 1):
            log(f"  {i:>3}. {p['pid']}  {p['name'][:64]}")
        log(f"dry run — nothing generated, nothing pushed ({len(targets)} would run, "
            f"parallel={args.parallel})")
        return
    if not targets:
        log("nothing to do — everything selected is already Complete "
            "(use --force to regenerate)")
        return

    done, failed = [], []
    started = time.time()
    counter = {"n": 0}
    count_lock = threading.Lock()

    def run_one(proc):
        with count_lock:
            counter["n"] += 1
            i = counter["n"]
        tag = f" [{i}/{len(targets)}]"
        try:
            return proc["pid"], process_one(proc, tr, tag=tag)
        except Exception as exc:                      # never let one kill the batch
            log(f"{proc['pid']}: unhandled error — {exc}", "ERROR")
            return proc["pid"], None

    try:
        if args.parallel > 1:
            log(f"running {args.parallel} workers in parallel")
            with ThreadPoolExecutor(max_workers=args.parallel) as pool:
                for pid, url in pool.map(run_one, targets):
                    (done if url else failed).append(pid)
        else:
            for proc in targets:
                pid, url = run_one(proc)
                (done if url else failed).append(pid)
    except KeyboardInterrupt:
        log("interrupted — publishing what is done", "WARN")

    mins = (time.time() - started) / 60
    if done:
        log(f"{len(done)} published in {mins:.1f} min "
            f"({mins / max(len(done), 1):.1f} min each)")
        rebuild_nav(tr, deploy=False)
    push_deploy()

    if done and not args.no_verify:
        url = f"{PAGES_BASE}/{BY_PID[done[-1]]['path']}"
        log("verified live: " + url if verify_live(url) else f"could not verify {url}")

    log(f"run complete — {len(done)} published, {len(failed)} failed"
        + (f" ({', '.join(failed)})" if failed else ""))


if __name__ == "__main__":
    main()
