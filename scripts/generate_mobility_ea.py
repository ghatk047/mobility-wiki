#!/usr/bin/env python3
"""
generate_mobility_ea.py — enterprise architecture diagrams for the Mobility Wiki.

    python3 scripts/generate_mobility_ea.py              # all 10
    python3 scripts/generate_mobility_ea.py --id ea-01   # one
    python3 scripts/generate_mobility_ea.py --id ea-03 --force

Shares config, sanitiser, backends, GitHub helpers and the sidebar with
generate_mobility_wiki.py, so both files must sit in the same scripts/ folder.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_mobility_wiki import (  # noqa: E402
    EA_DIAGRAMS, EA_DIR_SLUG, PAGES_BASE, DISCLAIMER,
    EA_W, EA_H, DIAGRAM_DIR, IMG_DIR, DATA_DIR,
    DEPTH_EA, DEPTH_EA_IDX, EA_FLOOR,
    SYSTEM_PROMPT_JSON, SYSTEM_PROMPT_MMD,
    call_model, model_ladder, backend_for, dump_raw, extract_json,
    sanitise_mermaid, fix_breaks, render_mermaid, finalize_svg, ea_richness,
    gh_push_file, push_deploy, verify_live, build_ea_index,
    page_shell, esc, sys_tags, prefix, confidence_badge,
    registry_brief, sparse_layers_for, log, load_tracker, save_tracker,
    L1_ARCHETYPES,
)

# Which L1 domain's registry slice grounds each EA diagram.
EA_DOMAIN = {
    "ea-01": "MD", "ea-02": "MD", "ea-03": "AV", "ea-04": "MF", "ea-05": "LM",
    "ea-06": "TS", "ea-07": "PF", "ea-08": "AM", "ea-09": "DD", "ea-10": "RC",
}

EA_JSON_SHAPE = """{
  "description": "3-4 sentence architecture description in the mobility platform context",
  "systems": ["Uber Michelangelo", "MDS 2.0", "Stripe Connect"],
  "layers": ["External Feeds", "Marketplace Core", "Operations Control", "Data"],
  "sourcing_confidence": "solid or partial or sparse",
  "sparse_layers": ["name any layer here whose real systems are not publicly documented"]
}"""

# Form reference from a different industry — the model copies the CONSTRUCT only.
FORM_EXAMPLE = """%%{init: {'theme':'base','themeVariables':{'fontSize':'13px','fontFamily':'Helvetica Neue, Helvetica, Arial, sans-serif'}}}%%
flowchart TB

  subgraph EXT["\U0001F310 External Feeds"]
    direction LR
    FAA["FAA SWIM\\nNOTAMs - TFRs - Slots"]
    WX["Jeppesen WSI\\nWeather - Winds - SIGMETs"]
  end

  subgraph DISPATCH["\U0001F4CB Dispatch and Flight Planning"]
    direction TB
    FP["NAVBLUE Lido\\nFlight plan - Fuel calc"]
    WB["Weight and Balance\\nLoad control - ZFW calc"]
    FAA -->|"NOTAMs - flow programs"| FP
    FP -->|"fuel load"| WB
  end

  subgraph NOC["\U0001F5A5 Operations Control"]
    direction TB
    SCOUT["Avtec Scout NOC\\nFlight watch - Gate - Crew"]
    DELAY["Delay Management\\nRoot cause - OTP tracking"]
    SCOUT -->|"delay codes"| DELAY
  end

  WX -->|"meteorological data"| SCOUT
  WB -->|"final load"| SCOUT

  classDef ext  fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e
  classDef disp fill:#fff7ed,stroke:#ea580c,color:#7c2d12
  classDef noc  fill:#ecfeff,stroke:#0891b2,color:#164e63
  classDef hero fill:#0f2a5c,color:#fff,stroke:#0f2a5c
  classDef sparse fill:#f8fafc,stroke:#94a3b8,color:#64748b,stroke-dasharray: 6 4

  class FAA,WX ext
  class FP,WB disp
  class SCOUT hero
  class DELAY noc"""


def ea_prompt(ea_id, title, scope, l1):
    sparse = sparse_layers_for(l1)
    sparse_block = ""
    if sparse:
        sparse_block = (
            "\nSPARSE LAYERS — these have NO public product names. Represent each as ONE node "
            "whose label names the FUNCTION and says sourcing is limited, and assign it to the "
            "`sparse` classDef so it renders dashed. Do NOT invent a vendor or product name:\n"
            + "\n".join(f'  * {s["layer"]} — {s["evidence_gap"]}' for s in sparse) + "\n"
        )
    return (
        f"Produce an enterprise architecture diagram for a mobility platform.\n"
        f"  Diagram ID : {ea_id.upper()}\n"
        f"  Title      : {title}\n"
        f"  Scope      : {scope}\n\n"
        f"GROUNDING BLOCK — verified facts, these override your training data:\n"
        f"{registry_brief(l1)}\n"
        f"{sparse_block}\n"
        "STRUCTURE — copy this construct exactly. It is from a different industry, so take\n"
        "the FORM and none of the content:\n\n"
        f"{FORM_EXAMPLE}\n\n"
        "REQUIREMENTS:\n"
        "- flowchart TB at the top level. Every subgraph declares its own direction TB or LR.\n"
        "- 5 to 7 subgraphs named for architecture layers, each title starting with one emoji.\n"
        "- 22 to 30 nodes. EVERY node label is two lines: real vendor or product name from the\n"
        "  grounding block, then a literal backslash-n, then 2 or 3 capabilities separated by\n"
        "  hyphens. Example: MDS[\"Mobility Data Specification 2.0\\nProvider API - Agency API - Policy API\"]\n"
        "- EVERY arrow carries a label naming the data that flows, in the form\n"
        "  A -->|\"trip telemetry\"| B. Unlabelled arrows are not acceptable.\n"
        "- Intra-layer arrows go inside their subgraph. Cross-layer arrows go after the last\n"
        "  subgraph closes.\n"
        "- Finish with at least 5 classDef lines and matching class assignment lines. Use\n"
        "  fill:#0f2a5c,color:#fff,stroke:#0f2a5c for the single most important system, and\n"
        "  ALWAYS include this exact line for undocumented layers:\n"
        "  classDef sparse fill:#f8fafc,stroke:#94a3b8,color:#64748b,stroke-dasharray: 6 4\n"
        "- Use only real system names from the grounding block. Do not invent product names.\n"
        "- Node IDs start with a letter. No parentheses, ampersands or angle brackets\n"
        "  anywhere in a label. Never use <br/> — use a literal backslash-n.\n"
    )


def generate_ea(ea_id, title, scope, l1):
    """Call 1 — narrative and systems only, no Mermaid."""
    backend = backend_for(l1)
    user = (
        f"Describe the enterprise architecture for a mobility platform.\n"
        f"  Diagram ID : {ea_id.upper()}\n  Title : {title}\n  Scope : {scope}\n\n"
        f"GROUNDING BLOCK — verified facts, these override your training data:\n"
        f"{registry_brief(l1)}\n\n"
        "Name 8 to 12 real systems from the grounding block that appear in this architecture.\n"
        "List in sparse_layers any layer whose real systems are not publicly documented.\n"
        "Do NOT include a mermaid field — the diagram is requested separately.\n\n"
        f"Return exactly this JSON shape and nothing else:\n{EA_JSON_SHAPE}\n"
    )
    for i in range(3):
        model = model_ladder(backend, i)
        try:
            raw = call_model(SYSTEM_PROMPT_JSON, user, backend,
                             temperature=0.25 + 0.1 * i, model=model)
            data = extract_json(raw, required=("systems",))
            if data and data.get("systems"):
                data.setdefault("layers", [])
                data.setdefault("sparse_layers", [])
                return data
            dump_raw(f"{ea_id}-json-{i+1}", raw)
            log(f"{ea_id}: unusable JSON from {model} (try {i+1}/3)", "WARN")
        except Exception as exc:
            log(f"{ea_id}: {backend} error on {model} — {exc}", "WARN")
        time.sleep(2)
    return None


def generate_ea_mermaid(ea_id, title, scope, l1, data, attempt=0):
    """Call 2 — raw Mermaid only."""
    backend = backend_for(l1)
    sys_list = ", ".join(str(s) for s in data.get("systems", [])[:12])
    user = ea_prompt(ea_id, title, scope, l1) + (
        f"\nSystems that must appear as nodes: {sys_list}\n"
        "Output the raw Mermaid and nothing else. No JSON, no fences, no commentary.\n"
    )
    model = model_ladder(backend, attempt)
    try:
        raw = call_model(SYSTEM_PROMPT_MMD, user, backend,
                         temperature=0.2 + 0.1 * attempt, model=model)
        return sanitise_mermaid(fix_breaks(raw))
    except Exception as exc:
        log(f"{ea_id}: mermaid call failed on {model} — {exc}", "WARN")
        return None


def render_ea(ea_id, title, scope, l1, data):
    """Score up to 3 drafts, publish the best as SVG plus a PNG for download."""
    mmd_path = DIAGRAM_DIR / f"{ea_id}.mmd"
    svg_path = IMG_DIR / f"{ea_id}.svg"
    png_path = IMG_DIR / f"{ea_id}.png"

    best, best_score, best_metrics = None, -1, {}
    for attempt in range(3):
        cand = generate_ea_mermaid(ea_id, title, scope, l1, data, attempt=attempt)
        score, metrics = ea_richness(cand)
        if cand and score > best_score:
            best, best_score, best_metrics = cand, score, metrics
        log(f"  {ea_id} draft {attempt+1}: score {score}/{len(EA_FLOOR)} {metrics}")
        if score >= len(EA_FLOOR) - 1:
            break
    if not best:
        return None, None
    if best_score < len(EA_FLOOR) - 2:
        short = [k for k, f in EA_FLOOR.items() if best_metrics.get(k, 0) < f]
        log(f"  {ea_id}: diagram UNDER FLOOR (score {best_score}/{len(EA_FLOOR)}, short on "
            f"{', '.join(short)}) — publishing anyway", "WARN")

    svg_ok = False
    for attempt in range(1, 4):
        svg_ok, info = render_mermaid(best, mmd_path, svg_path, EA_W, EA_H)
        if svg_ok:
            finalize_svg(svg_path)
            log(f"  {ea_id} rendered as SVG ({info})")
            break
        log(f"  {ea_id} SVG render attempt {attempt}/3 failed: {info}", "WARN")
        retry = generate_ea_mermaid(ea_id, title, scope, l1, data, attempt=attempt)
        if retry:
            best = retry
    if not svg_ok:
        return None, None

    png_out = None
    for w, h, scale in [(EA_W, EA_H, 2), (EA_W, EA_H, 1), (2560, 1440, 2)]:
        ok, info = render_mermaid(best, mmd_path, png_path, w, h, scale=scale)
        if ok:
            log(f"  {ea_id} PNG fallback at {w}x{h} scale {scale} ({info})")
            png_out = png_path
            break
    return svg_path, png_out


def build_ea_page(ea_id, title, scope, data):
    p = prefix(DEPTH_EA)
    conf = data.get("sourcing_confidence", "partial")
    sparse = data.get("sparse_layers") or []
    sparse_html = ""
    if sparse:
        items = "".join(f"<li>{esc(s)}</li>" for s in sparse)
        sparse_html = f"""
      <div class="card sparse-card">
        <div class="card-header">&#x26A0; Layers With Limited Public Sourcing</div>
        <div class="card-body">
          <p>These layers render <strong>dashed</strong> in the diagram above. Their real
             systems are not publicly documented, so this wiki names the function rather
             than inventing a product name.</p>
          <ul class="sparse-list">{items}</ul>
        </div>
      </div>"""

    main = f"""      <div class="page-header">
        <div class="breadcrumb">
          <a href="{p}index.html">Home</a> &rsaquo;
          <a href="../index.html">Enterprise Architecture</a>
        </div>
        <h1><span class="pid-badge tier-1">EA</span> {ea_id.upper()} &mdash; {esc(title)}</h1>
        <p>{esc(scope)}</p>
        <p class="badge-row">{confidence_badge(conf)}</p>
      </div>

      <div class="card">
        <div class="card-header">&#x1F5FA; Architecture Diagram &mdash; 4K, click to zoom</div>
        <div class="card-body">
          <div class="diagram-wrap">
            <a href="{p}assets/img/{ea_id}.svg" data-lightbox data-title="{ea_id.upper()} {esc(title)}">
              <img src="{p}assets/img/{ea_id}.svg" alt="{ea_id.upper()} {esc(title)}">
            </a>
            <p>Vector diagram &mdash; stays sharp at any zoom &bull; Scroll to zoom &bull;
               Drag to pan &bull; <a href="{p}assets/img/{ea_id}.svg" download>Download SVG</a>
               &bull; <a href="{p}assets/img/{ea_id}.png" download>Download PNG</a></p>
          </div>
        </div>
      </div>
{sparse_html}
      <div class="card">
        <div class="card-header">&#x1F4CB; Diagram Details</div>
        <div class="card-body">
          <table class="attr-table">
            <tr><th>Diagram ID</th><td>{ea_id.upper()}</td></tr>
            <tr><th>Title</th><td>{esc(title)}</td></tr>
            <tr><th>Scope</th><td>{esc(scope)}</td></tr>
            <tr><th>Architecture Layers</th><td>{esc(", ".join(str(l) for l in data.get('layers', []))) or '<span class="text-muted">Not captured</span>'}</td></tr>
            <tr><th>Key Systems</th><td>{sys_tags(data.get('systems'))}</td></tr>
            <tr><th>Description</th><td>{esc(data.get('description', scope))}</td></tr>
          </table>
        </div>
      </div>
"""
    return page_shell(f"{ea_id.upper()} &mdash; {esc(title)}", "Enterprise Architecture",
                      DEPTH_EA, main, active_ea=ea_id)


def main():
    ap = argparse.ArgumentParser(description="Mobility wiki EA diagram generator")
    ap.add_argument("--id", help="single diagram, e.g. ea-01")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()

    for d in (DATA_DIR, DIAGRAM_DIR, IMG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    tr = load_tracker()

    targets = EA_DIAGRAMS
    if args.id:
        wanted = args.id.lower()
        targets = [d for d in EA_DIAGRAMS if d[0] == wanted]
        if not targets:
            sys.exit(f"Unknown diagram {args.id}. "
                     f"Valid: {', '.join(d[0] for d in EA_DIAGRAMS)}")
    if not args.force:
        targets = [t for t in targets if tr.get(t[0], {}).get("status") != "Complete"]

    done, failed = [], []
    try:
        for ea_id, title, scope in targets:
            l1 = EA_DOMAIN.get(ea_id, "MD")
            log(f"── {ea_id.upper()} — {title}  [backend: {backend_for(l1)}, registry: {l1}]")
            data = generate_ea(ea_id, title, scope, l1)
            if not data:
                failed.append(ea_id)
                continue
            svg, png = render_ea(ea_id, title, scope, l1, data)
            if not svg:
                log(f"{ea_id}: diagram failed after 3 attempts — skipped", "ERROR")
                failed.append(ea_id)
                continue
            if not gh_push_file(f"assets/img/{ea_id}.svg", svg.read_bytes(),
                                f"Add {ea_id.upper()} diagram"):
                failed.append(ea_id)
                continue
            if png:
                gh_push_file(f"assets/img/{ea_id}.png", png.read_bytes(),
                             f"Add {ea_id.upper()} PNG download")
            if not gh_push_file(f"{EA_DIR_SLUG}/{ea_id}/index.html",
                                build_ea_page(ea_id, title, scope, data),
                                f"Add {ea_id.upper()} {title}"):
                failed.append(ea_id)
                continue
            tr[ea_id] = {"status": "Complete",
                         "url": f"{PAGES_BASE}/{EA_DIR_SLUG}/{ea_id}/index.html"}
            save_tracker(tr)
            done.append(ea_id)
            log(f"  pushed {ea_id}")
    except KeyboardInterrupt:
        log("interrupted — publishing what is done", "WARN")

    gh_push_file(f"{EA_DIR_SLUG}/index.html", build_ea_index(), "Update EA index")
    push_deploy()

    if done and not args.no_verify:
        url = f"{PAGES_BASE}/{EA_DIR_SLUG}/{done[-1]}/index.html"
        log("verified live: " + url if verify_live(url) else f"could not verify {url}")

    log(f"EA run complete — {len(done)} published, {len(failed)} failed"
        + (f" ({', '.join(failed)})" if failed else ""))


if __name__ == "__main__":
    main()
