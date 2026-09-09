#!/usr/bin/env bash
#
# run.sh — driver for the Mobility & Micromobility Process Wiki generator.
#
# Everything runs SEQUENTIALLY, one item at a time. The -n parameter says how
# many to do in this batch before stopping.
#
#   ./run.sh gen -n 5        generate the next 5 process pages, one after another
#   ./run.sh gen -n 50       generate the next 50
#   ./run.sh ea -n 3         generate the next 3 EA diagrams
#
# Secrets are read from the environment only and never written to a file.
# GITHUB_TOKEN is pulled from the gh keychain at run time.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/data/logs"
PY=python3

# ── colours (disabled when not a tty) ────────────────────────────────────────
if [[ -t 1 ]]; then
  R=$'\e[31m'; G=$'\e[32m'; Y=$'\e[33m'; DIM=$'\e[2m'; BOLD=$'\e[1m'; N=$'\e[0m'
else
  R=""; G=""; Y=""; DIM=""; BOLD=""; N=""
fi
say()  { printf '%s\n' "$*"; }
ok()   { printf '%s✓%s %s\n' "$G" "$N" "$*"; }
warn() { printf '%s!%s %s\n' "$Y" "$N" "$*"; }
die()  { printf '%s✗%s %s\n' "$R" "$N" "$*" >&2; exit 1; }
hdr()  { printf '\n%s%s%s\n' "$BOLD" "$*" "$N"; }

usage() {
cat <<'EOF'
Mobility Wiki generator — everything runs one at a time, sequentially.

USAGE
  ./run.sh <command> [options]

COMMANDS
  status              Show progress: complete / remaining, per domain
  preflight           Check ollama, mmdc, chrome, token, registries
  bootstrap           Push the site shell and all 93 index pages (run once)
  gen                 Generate PROCESS pages   (357 total)
  ea                  Generate EA DIAGRAMS     (10 total)
  nav                 Rebuild and push every index page (no model calls)
  test                Run the sanitiser + taxonomy self-tests
  help                This message

OPTIONS
  -n, --count N       How many to generate in this batch, run one after
                      another. Default 5. Use 50 for a long unattended run.
      --all           Everything still incomplete (ignores -n)
  -p, --pid PID       One specific process, e.g. MM-AV-RA-01
      --id ID         One specific EA diagram, e.g. ea-03
      --start PID     Begin the batch from this PID in catalogue order
      --force         Regenerate even if already marked Complete
      --dry-run       List what would run; generate and push nothing
      --verify        Wait ~90s afterwards and confirm a page is live
  -q, --quiet         Log to file only, print just the summary

PROCESS PAGES  (the 357 PIDs)
  ./run.sh gen -n 5                    next 5, sequentially
  ./run.sh gen -n 50                   next 50, sequentially
  ./run.sh gen -n 10 --dry-run         show the queue, run nothing
  ./run.sh gen --all                   everything remaining
  ./run.sh gen -p MM-AV-RA-01          just that one process
  ./run.sh gen -p MM-AV-RA-01 --force  redo it even if Complete
  ./run.sh gen -n 20 --start MM-MF-CH-01   20 starting from that PID
  ./run.sh gen -n 50 -q                long run, quiet, tail the log

EA DIAGRAMS  (ea-01 … ea-10)
  ./run.sh ea -n 3                     next 3 EA diagrams
  ./run.sh ea --all                    all remaining EA diagrams
  ./run.sh ea --id ea-03               just that one diagram
  ./run.sh ea --id ea-03 --force       redo it even if Complete
  ./run.sh ea --dry-run                show which are outstanding

TYPICAL FIRST RUN
  ./run.sh preflight
  ./run.sh bootstrap
  ./run.sh ea --all
  ./run.sh gen -n 50

TIMING
  About 7-12 minutes per process page on qwen2.5-coder:14b, because each one
  makes a content call plus up to three scored diagram drafts. -n 50 is
  roughly a 7-9 hour run; start it with -q and tail the log.
EOF
}

# ── environment ──────────────────────────────────────────────────────────────
setup_env() {
  export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"

  if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
      GITHUB_TOKEN="$(gh auth token)"
      export GITHUB_TOKEN
    fi
  fi

  # mmdc needs a Chrome it can actually find; puppeteer's copy is the reliable one
  if [[ -z "${PUPPETEER_EXECUTABLE_PATH:-}" ]]; then
    local c
    c="$(ls -d "$HOME"/.cache/puppeteer/chrome/*/chrome-mac-arm64/"Google Chrome for Testing.app"/Contents/MacOS/"Google Chrome for Testing" 2>/dev/null | sort -V | tail -1 || true)"
    [[ -z "$c" ]] && c="$(ls -d "$HOME"/.cache/puppeteer/chrome/*/chrome-linux64/chrome 2>/dev/null | sort -V | tail -1 || true)"
    [[ -n "$c" ]] && export PUPPETEER_EXECUTABLE_PATH="$c"
  fi
}

preflight() {
  local fail=0
  hdr "Preflight"

  if curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
    ok "ollama reachable at localhost:11434"
    if curl -s --max-time 5 http://localhost:11434/api/tags | grep -q 'qwen2.5-coder:14b'; then
      ok "model qwen2.5-coder:14b present"
    else
      warn "qwen2.5-coder:14b not found — run: ollama pull qwen2.5-coder:14b"; fail=1
    fi
  else
    warn "ollama not reachable — start it with: ollama serve"; fail=1
  fi

  if command -v mmdc >/dev/null 2>&1; then
    ok "mmdc $(mmdc --version 2>/dev/null | tail -1)"
  else
    warn "mmdc not on PATH — npm i -g @mermaid-js/mermaid-cli"; fail=1
  fi

  if [[ -n "${PUPPETEER_EXECUTABLE_PATH:-}" && -x "${PUPPETEER_EXECUTABLE_PATH:-}" ]]; then
    ok "chrome for mmdc found"
  else
    warn "no chrome found for mmdc. Fix with:"
    say  "    npx puppeteer browsers install chrome"
    say  "    export PUPPETEER_EXECUTABLE_PATH=<path to the installed binary>"
    fail=1
  fi

  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    ok "GITHUB_TOKEN present (${#GITHUB_TOKEN} chars, ${GITHUB_TOKEN:0:4}…)"
  else
    warn "GITHUB_TOKEN not set and gh not authenticated. Fix with: gh auth login"; fail=1
  fi

  local missing=0
  for f in companies systems regulations kpis roles; do
    [[ -f "registries/$f.json" ]] || { warn "registries/$f.json missing"; missing=1; }
  done
  (( missing == 0 )) && ok "all 5 registries present" || fail=1

  if $PY scripts/taxonomy.py >/dev/null 2>&1; then
    ok "taxonomy validates (357 processes / 18 domains / 74 groups)"
  else
    warn "taxonomy.py failed its assertions"; fail=1
  fi

  echo
  (( fail == 0 )) && ok "ready" || die "preflight failed — fix the items above"
}

status() {
  $PY - <<'PYEOF'
import json, sys, collections
from pathlib import Path
sys.path.insert(0, "scripts")
from taxonomy import PROCESSES, L1_META, TIER_LABEL

tr = {}
p = Path("data/processes.json")
if p.exists():
    try: tr = json.loads(p.read_text())
    except Exception: pass

done = {k for k, v in tr.items() if v.get("status") == "Complete"}
proc_done = sum(1 for x in PROCESSES if x["pid"] in done)
ea_done = sum(1 for k in done if k.startswith("ea-"))
total = len(PROCESSES)

bar_w = 40
filled = int(bar_w * proc_done / total)
print(f"\n\033[1mMobility Wiki — progress\033[0m")
print(f"  [{'#'*filled}{'.'*(bar_w-filled)}] {proc_done}/{total} processes "
      f"({100*proc_done//total}%)   EA: {ea_done}/10\n")

per = collections.Counter(x["l1"] for x in PROCESSES if x["pid"] in done)
tot = collections.Counter(x["l1"] for x in PROCESSES)
for tier in (1, 2, 3):
    print(f"  \033[2m{TIER_LABEL[tier]}\033[0m")
    for code, (icon, name, slug, t) in L1_META.items():
        if t != tier: continue
        d, n = per[code], tot[code]
        mark = "\033[32m✓\033[0m" if d == n else " "
        print(f"    {mark} {code}  {name[:38]:<38} {d:>3}/{n:<3}")
    print()

nxt = [x for x in PROCESSES if x["pid"] not in done][:3]
if nxt:
    print("  next up:")
    for x in nxt:
        print(f"    {x['pid']}  {x['name'][:60]}")
    remaining = total - proc_done
    print(f"\n  {remaining} left — roughly {remaining*9//60}h{remaining*9%60:02d}m at ~9 min each")
else:
    print("  \033[32mall processes complete\033[0m")
print()
PYEOF
}

# ── argument parsing ─────────────────────────────────────────────────────────
CMD="${1:-help}"; shift || true

COUNT=5; PID=""; EAID=""; START=""; ALL=0; FORCE=0; DRY=0; VERIFY=0; QUIET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--count)  COUNT="${2:?--count needs a number}"; shift 2 ;;
    -p|--pid)    PID="${2:?--pid needs a PID}"; shift 2 ;;
    --id)        EAID="${2:?--id needs a diagram id}"; shift 2 ;;
    --start)     START="${2:?--start needs a PID}"; shift 2 ;;
    --all)       ALL=1; shift ;;
    --force)     FORCE=1; shift ;;
    --dry-run)   DRY=1; shift ;;
    --verify)    VERIFY=1; shift ;;
    -q|--quiet)  QUIET=1; shift ;;
    -h|--help)   usage; exit 0 ;;
    *)           die "unknown option: $1  (try ./run.sh help)" ;;
  esac
done

[[ "$COUNT" =~ ^[0-9]+$ ]] || die "--count must be a number"
(( COUNT >= 1 )) || die "--count must be at least 1"

setup_env
mkdir -p "$LOG_DIR"

run_logged() {
  local label="$1"; shift
  local logfile="$LOG_DIR/${label}-$(date +%Y%m%d-%H%M%S).log"
  say "${DIM}logging to ${logfile}${N}"
  if (( QUIET )); then
    "$@" >"$logfile" 2>&1 || true
    tail -8 "$logfile"
  else
    set +e
    "$@" 2>&1 | tee "$logfile"
    set -e
  fi
  say "${DIM}full log: ${logfile}${N}"
}

case "$CMD" in
  help|-h|--help) usage ;;
  preflight)      preflight ;;
  status)         status ;;

  test)
    hdr "Self-tests"
    $PY scripts/test_sanitiser.py | tail -3
    $PY scripts/taxonomy.py | tail -3
    ok "tests passed"
    ;;

  bootstrap)
    preflight
    hdr "Bootstrapping site shell + 93 index pages"
    run_logged bootstrap $PY scripts/generate_mobility_wiki.py --bootstrap
    ok "bootstrap done — https://ghatk047.github.io/mobility-wiki/"
    ;;

  nav)
    hdr "Rebuilding indexes"
    run_logged nav $PY scripts/generate_mobility_wiki.py --rebuild-nav
    ok "indexes rebuilt"
    ;;

  # ── EA DIAGRAMS ────────────────────────────────────────────────────────────
  ea)
    (( DRY )) || preflight
    ARGS=()
    (( DRY ))   && ARGS+=(--dry-run)
    (( FORCE )) && ARGS+=(--force)
    (( VERIFY )) || ARGS+=(--no-verify)
    if   [[ -n "$EAID" ]]; then ARGS+=(--id "$EAID")
    elif (( ALL ));        then :                       # generator does all outstanding
    else                        ARGS+=(--count "$COUNT")
    fi
    hdr "EA diagrams — sequential$( [[ -n "$EAID" ]] && echo " ($EAID)" || { (( ALL )) && echo " (all remaining)" || echo " (batch of $COUNT)"; } )"
    run_logged ea $PY scripts/generate_mobility_ea.py "${ARGS[@]}"
    ;;

  # ── PROCESS PAGES ──────────────────────────────────────────────────────────
  gen)
    (( DRY )) || preflight
    ARGS=()
    (( DRY ))   && ARGS+=(--dry-run)
    (( FORCE )) && ARGS+=(--force)
    (( VERIFY )) || ARGS+=(--no-verify)
    if   [[ -n "$PID" ]]; then ARGS+=(--pid "$PID")
    elif (( ALL ));       then ARGS+=(--full)
    else                       ARGS+=(--count "$COUNT")
    fi
    [[ -n "$START" ]] && ARGS+=(--start "$START")

    hdr "Process pages — sequential$( [[ -n "$PID" ]] && echo " ($PID)" || { (( ALL )) && echo " (all remaining)" || echo " (batch of $COUNT)"; } )"
    if (( ! DRY )) && (( COUNT >= 20 )) && [[ -z "$PID" ]]; then
      say "${DIM}~$((COUNT*9/60))h$((COUNT*9%60))m at roughly 9 min each. Ctrl-C is safe —"
      say "finished pages stay published and the tracker resumes where it stopped.${N}"
    fi
    run_logged gen $PY scripts/generate_mobility_wiki.py "${ARGS[@]}"
    (( DRY )) || status
    ;;

  *) die "unknown command: $CMD  (try ./run.sh help)" ;;
esac
