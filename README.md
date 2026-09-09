# Mobility &amp; Micromobility Process Wiki

**Live site → <https://ghatk047.github.io/mobility-wiki/>**

A homogeneous business-process taxonomy spanning six genuinely different mobility operating
models that share a marketplace and dispatch core: ride-hail, autonomous ride-hail, last-mile
delivery, micromobility, eVTOL air mobility and drone delivery.

**357 processes · 18 L1 domains · 74 L2 process groups · 10 enterprise-architecture diagrams**

Every page carries a BPMN process flow rendered as a zoomable vector, an L4 step table with
roles, systems, inputs, outputs, KPIs and pain points, plus a KPI and risk register — all
generated against a registry of researched, sourced facts rather than model recall.

---

## Contents

- [Why this exists](#why-this-exists)
- [The six archetypes](#the-six-archetypes)
- [Taxonomy](#taxonomy)
- [Sourcing discipline](#sourcing-discipline)
- [Quick start](#quick-start)
- [Command reference](#command-reference)
- [How generation works](#how-generation-works)
- [Quality gates](#quality-gates)
- [Repository layout](#repository-layout)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Disclaimer](#disclaimer)

---

## Why this exists

Mobility is usually documented one company at a time, which hides the thing that actually
matters: Uber, Waymo, DoorDash, Lime, Joby and Zipline all run a **matching engine over a
supply pool against geospatial demand**, and then diverge completely in what the supply is,
who or what operates it, and which regulator governs it.

This wiki models that explicitly with a three-tier taxonomy — a shared marketplace core, a
layer of archetype-specific operations, and a cross-cutting enterprise spine — rather than
forcing every archetype into one shape or fragmenting into six disconnected mini-wikis.

---

## The six archetypes

Operating status verified by web research on **2026-09-09**. Several of these are materially
different from their general public profile, which is precisely why the registry exists.

| Archetype | Reference companies | 2026 status |
|---|---|---|
| Ride-hail | Uber, Lyft | Operating, profitable. Uber Q2-26 gross bookings $58.0B (+24%), first TTM FCF over $10B. Lyft Q2-26 revenue $1.84B (+16.1%). |
| Autonomous ride-hail | Waymo | 14 US metros as of 1 Sep 2026, ~2,500 vehicles. **Freeway operations paused nationwide since 21 May 2026.** |
| Last-mile delivery | DoorDash | Acquired Deliveroo; launched Dot (in-house robot) and **DoorDash Air under its own FAA Part 135 certificate**. |
| Micromobility | Bird, Lime, Bolt | **Bird is not an independent company** — Chapter 11 in Dec 2023, now a brand of Third Lane Mobility. Lime IPO'd on Nasdaq July 2026 with a going-concern warning. Bolt is the healthy archetype: 230k+ vehicles, 270+ cities. |
| eVTOL air mobility | Joby, Archer, Wisk | **All pre-revenue.** Joby cleared FAA Stage 4 (Mar 2026); Archer at Phase 3 of 4; Wisk targets certification "before the end of the decade". |
| Drone delivery | Zipline, Wing, Amazon Prime Air | Operating at scale. Zipline passed 2M deliveries (Jan 2026). **FAA Part 108 is still an NPRM** — no operator holds Part 108 authority. |

Full detail with per-fact sources lives in [`registries/companies.json`](registries/companies.json).

---

## Taxonomy

PID format: **`MM-{L1}-{L2}-{NN}`** — for example `MM-AV-RA-03`.

### Tier 1 — Shared marketplace core (6 domains, 122 processes)

Applies to every archetype. Processes here are written to hold across all of them, with the
differences pushed into an *Archetype Variation* field.

| L1 | Domain | Groups | N |
|---|---|---|---|
| `MD` | Marketplace Matching &amp; Dispatch | Demand forecasting · Matching &amp; assignment · Routing/ETA · Batching &amp; pooling | 22 |
| `PX` | Dynamic Pricing &amp; Incentives | Surge · Supply incentives · Demand promotions · Subscriptions | 18 |
| `SL` | Driver, Courier &amp; Rider Lifecycle | Onboarding · Ratings · Deactivation &amp; appeals · Rider accounts · Gig classification | 23 |
| `TS` | Trust &amp; Safety | Background checks · Incident response · Insurance &amp; claims · Fraud | 22 |
| `PF` | Payments &amp; Financial Operations | Consumer payments · Payouts · Tax &amp; 1099 · Revenue recognition | 19 |
| `CX` | Customer Experience &amp; Support | Support ops · Resolution &amp; refunds · Accessibility · Voice of customer | 18 |

### Tier 2 — Archetype-specific operations (5 domains, 120 processes)

The reason this is not just an Uber wiki.

| L1 | Domain | Groups | N |
|---|---|---|---|
| `AV` | Autonomous Vehicle Operations | Driverless fleet &amp; depot · Remote assistance · Safety case &amp; disengagement · AV permitting | 25 |
| `MF` | Micromobility Fleet Operations | Charging &amp; swap · Rebalancing · Telemetry &amp; IoT · Parking &amp; right-of-way | 25 |
| `LM` | Last-Mile Delivery Operations | Merchant integration · Courier dispatch · Order fulfilment · Dark stores | 24 |
| `AM` | eVTOL &amp; Advanced Air Mobility | Type certification · Part 135 flight ops · Vertiport ops · Airspace integration | 23 |
| `DD` | Drone Delivery Operations | BVLOS authorisation · Nest ops · Package handling · Deconfliction &amp; DAA | 23 |

### Tier 3 — Cross-cutting enterprise (7 domains, 115 processes)

| L1 | Domain | Groups | N |
|---|---|---|---|
| `VA` | Vehicle &amp; Asset Management | Acquisition · Maintenance · Lifecycle · Warranty &amp; parts | 17 |
| `RC` | Regulatory &amp; Municipal Compliance | TNC licensing · Municipal permits · Data privacy · AV &amp; aviation affairs · Labour ordinance | 24 |
| `TD` | Technology, Data &amp; Mapping | Mapping · ML platform · Platform reliability · Telematics | 20 |
| `GM` | Marketing &amp; Growth | Performance marketing · Brand · City launch · Loyalty | 13 |
| `FN` | Finance, Accounting &amp; IR | Planning · Close &amp; controls · Treasury · Investor relations | 15 |
| `HR` | HR &amp; Corporate Workforce | Talent · People ops · Frontline · Culture | 12 |
| `SE` | Sustainability &amp; Fleet Electrification | EV transition · Carbon accounting · Battery circularity · Urban impact | 14 |

Verify the counts at any time:

```bash
python3 scripts/taxonomy.py
```

---

## Sourcing discipline

The local model (`qwen2.5-coder:14b`) has a training cutoff and cannot reach the internet. On a
vertical that moves this fast it will confidently go stale or fabricate. Two mechanisms guard
against that.

### 1. Registries ground every generation

Five JSON registries are compiled from web research and injected into every prompt as a
grounding block that explicitly overrides the model's training data:

| Registry | Contents |
|---|---|
| [`companies.json`](registries/companies.json) | 13 entities with verified 2026 operating status, per-fact sources, and modelling notes |
| [`systems.json`](registries/systems.json) | 56 real platforms across 7 archetype slices, plus 6 declared sparse layers |
| [`regulations.json`](registries/regulations.json) | 26 real citations — FAA Part 107/108/135, ASTM F3548-21, CPUC D.18-05-043, Prop 22, MDS 2.0, GDPR… |
| [`kpis.json`](registries/kpis.json) | 106 KPI patterns across 18 domains, each marked `measured` (sourced value) or `pattern` (metric name only) |
| [`roles.json`](registries/roles.json) | 115 real role titles across 18 domains |

After generation, every page is validated back against the registries. Any system, role or
citation that isn't sourced is logged as a warning:

```
VALIDATION MM-MD-DM-01: clean — all systems, roles and citations sourced
```

### 2. Sparse entries stay visibly sparse

Some things are genuinely not public: **Waymo's production autonomy stack** is trade secret,
and **eVTOL operational procedure** does not exist yet because no operator has carried a paying
passenger. Padding those with invented product names would make the wiki look complete and be
worse than useless.

Instead they are declared as `sparse_layers`, pages carry a **Sparse sourcing** badge, and the
EA diagrams render those nodes **dashed** via a dedicated `classDef`:

```
classDef sparse fill:#f8fafc,stroke:#94a3b8,color:#64748b,stroke-dasharray: 6 4
```

A thin registry that is honest beats a full one that is fabricated.

> **Regulatory caution.** FAA Part 108 is an **NPRM only** — published 7 Aug 2025, held in OIRA
> review since 10 Jul 2026, unpublished as of 29 Aug 2026. The registry flags it
> `must_be_labelled_proposed`, and no page may present it as in force.

---

## Quick start

### Prerequisites

| Requirement | Check |
|---|---|
| [Ollama](https://ollama.com) with `qwen2.5-coder:14b` | `ollama pull qwen2.5-coder:14b` |
| [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) | `npm i -g @mermaid-js/mermaid-cli` |
| Chrome for mmdc | `npx puppeteer browsers install chrome` |
| GitHub auth | `gh auth login` |
| Python 3 with `requests` | `pip3 install requests` |

### First run

```bash
git clone https://github.com/ghatk047/mobility-wiki.git
cd mobility-wiki
./run.sh preflight
```

```bash
./run.sh bootstrap
```

```bash
./run.sh ea --all
```

```bash
./run.sh gen -n 50
```

`preflight` checks Ollama, the model, mmdc, Chrome, the token and all five registries before
anything runs.

---

## Command reference

Everything runs **sequentially, one item at a time**. `-n` is the batch size.

### Process pages

```bash
./run.sh gen -n 5                      # next 5
./run.sh gen -n 50                     # next 50
./run.sh gen --all                     # everything remaining
./run.sh gen -n 10 --dry-run           # show the queue, generate nothing
./run.sh gen -p MM-AV-RA-01            # one specific process
./run.sh gen -p MM-AV-RA-01 --force    # redo it even if Complete
./run.sh gen -n 20 --start MM-MF-CH-01 # 20 starting from that PID
./run.sh gen -n 50 -q                  # long run, quiet, log to file
```

### EA diagrams

```bash
./run.sh ea -n 3                       # next 3
./run.sh ea --all                      # all remaining
./run.sh ea --id ea-03                 # one specific diagram
./run.sh ea --id ea-03 --force         # redo it
./run.sh ea --dry-run                  # show which are outstanding
```

### Everything else

```bash
./run.sh status         # progress board, per domain, with ETA
./run.sh preflight      # environment checks
./run.sh test           # sanitiser + taxonomy self-tests
./run.sh nav            # rebuild and push every index (no model calls)
./run.sh help           # full usage
```

### Options

| Flag | Meaning |
|---|---|
| `-n, --count N` | how many to run in this batch (default 5) |
| `--all` | everything still incomplete |
| `-p, --pid PID` | one specific process |
| `--id ID` | one specific EA diagram |
| `--start PID` | begin the batch from this PID |
| `--force` | regenerate something already marked Complete |
| `--dry-run` | list what would run; generate and push nothing |
| `--verify` | wait ~90s afterwards and confirm a page is live |
| `-q, --quiet` | log to file only, print the summary |

**Resumable.** A local tracker records what's done, so `-n 50` five times gets you 250 pages.
Ctrl-C is safe: tracker writes are atomic (temp file + rename), finished pages stay published,
and an interrupted PID returns to the front of the queue.

**Timing.** Roughly 7–12 minutes per process page — one content call plus up to three scored
diagram drafts. `-n 50` is about a 7–9 hour run.

> **On parallelism.** Deliberately not exposed. Measured on a 16 GB host with a 9 GB model:
> two concurrent Ollama requests took 13.9s versus 15.9s sequential (~13%), and a real
> two-worker batch spent **8 minutes on a single content call** from contention. The generator
> still accepts `-j N`, but `run.sh` never passes it. To go faster, route domains to OpenRouter
> in `BACKEND_CONFIG` instead — those calls genuinely parallelise and are not RAM-bound.

---

## How generation works

```
 registries/*.json ──┐
                     ├──► CALL 1  content JSON  (no Mermaid allowed)
 taxonomy.py ────────┘         │
                               ▼
                         validate vs registries
                               │
                               ▼
                     CALL 2  raw Mermaid only  ◄──┐
                               │                  │ repair directive
                               ▼                  │ (names the model's own
                    sanitise → score → gates ─────┘  rejected labels back)
                               │  up to 3 drafts
                               ▼
                     mmdc → SVG → finalize_svg
                               │
                               ▼
                    GitHub Contents API (SHA + backoff)
                               │
                               ▼
                     .deploy pushed LAST → Pages rebuild
```

**Two calls, never one.** Call 1 returns content JSON and is explicitly forbidden from emitting
Mermaid — a lightweight model that injects a diagram into the JSON breaks extraction. Call 2
returns raw Mermaid only, so a multi-line label never has to survive JSON string escaping,
which is where `\n` gets flattened.

**Tolerant JSON extraction.** Strips `%%{init…}%%` blocks and `flowchart` lines before scanning,
walks every balanced brace-delimited object, and returns the first that parses *and* carries the
required key. Unparseable responses are saved to `data/raw/<id>-json-<n>.txt`.

**Sanitiser.** Ported from a sibling project where each step was a shipped defect. The subtle
one: any regex rewriting digit-leading node IDs (`1.1` → `S1_1`) will also mangle
`FAA Part 107.31`, `ASTM F3548-21` and `CPUC Decision 18-05-043` unless label text is stashed
and restored around that step. `scripts/test_sanitiser.py` asserts both properties hold.

**Font enforcement.** `fontFamily` must sit at the **top level** of the init config — mermaid v11
silently ignores it inside `themeVariables` and falls back to Trebuchet. An SVG loaded via
`<img>` cannot fetch webfonts, so this is what keeps text from going soft.

**SVG finalisation.** mmdc emits `width="100%"` plus an inline `max-width` that caps how large
the vector will ever render, producing exactly the blur-on-zoom a raster would. Both are
replaced with real viewBox dimensions, and **every** `max-width` is stripped so
`grep -c 'max-width'` returns `0`.

**Lightbox.** Zoom changes layout `width`, never `transform: scale()`, with no `will-change` and
an absolutely-positioned overlay — so the browser re-rasterises the vector at each new size
instead of magnifying a cached bitmap.

---

## Quality gates

Floors were **measured** from the sibling repos' own diagrams (n=149 airline `.mmd`, n=16
shipping `.svg`), not invented.

### Scored metrics — one point each

| Metric | Floor | Reference median |
|---|---|---|
| nodes | ≥ 30 | 30 |
| decisions | ≥ 6 | 6 |
| branches (unique) | ≥ 12 | 12 |
| subgraphs | ≥ 5 | 5 |
| style lines | ≥ 8 | 8 |
| terminators | **band 2–6** | 2 |

### Hard gates — a draft failing one is rejected regardless of score

| Gate | Requirement | Why |
|---|---|---|
| `loops` | ≥ 2 rework cycles | A flow whose every failed decision dead-ends in its own exception terminator is a linear checklist, not a process. Detected as true graph cycles (DFS back-edges). Reference median is 4. |
| `substantive_decisions` | ≥ 3 | A decision that only asks whether the previous step worked ("Ingestion successful?") is error handling. Each must name a threshold or business condition. Reference median is 3. |

Prose instructions alone did not achieve this — the model produced 9 degenerate decisions and 0
substantive ones across three drafts even with an anti-pattern example in the prompt. So a
rejected draft's **own offending labels are fed back verbatim** into the next attempt. Diagrams
are scored up to 3 times; the best is published, and any remaining gate failure is logged by ID.

EA diagrams use their own floors: ≥ 22 nodes, ≥ 12 labelled edges, ≥ 5 subgraphs, ≥ 5 classDefs.

---

## Repository layout

```
mobility-wiki/
├── run.sh                          driver — preflight, status, gen, ea, nav, test
├── scripts/
│   ├── taxonomy.py                 357 processes / 18 domains / 74 groups, self-asserting
│   ├── generate_mobility_wiki.py   process generator, sanitiser, backends, GitHub, HTML
│   ├── generate_mobility_ea.py     enterprise-architecture diagram generator
│   └── test_sanitiser.py           19 assertions: citations survive, node IDs still fixed
├── registries/
│   ├── companies.json              13 entities, verified 2026 status, sources
│   ├── systems.json                56 systems, 7 archetype slices, 6 sparse layers
│   ├── regulations.json            26 real citations
│   ├── kpis.json                   106 KPI patterns
│   └── roles.json                  115 role titles
├── assets/
│   ├── css/wiki.css                three-tier palette, sparse badges, lightbox
│   ├── js/wiki.js                  sidebar accordion, width-based zoom lightbox, search
│   └── img/                        published SVG + PNG diagrams
├── diagrams/                       generated .mmd sources
├── data/                           local only, never pushed (tracker, logs, raw responses)
├── ea-diagrams/                    10 EA diagram pages
└── <18 domain dirs>/<74 group dirs>/<pid>/index.html
```

Generated pages carry a template version stamp so a later pass can find stale ones:

```html
<!-- mobility-wiki template v1.0.0 -->
```

---

## Configuration

### Model backends

A single `call_model(system_prompt, user_prompt, backend)` dispatches to either Ollama's
`/api/generate` or OpenRouter's OpenAI-compatible `/v1/chat/completions`. Whichever produces the
draft, it goes through the **identical** downstream pipeline — same two-call split, same
sanitiser, same scoring, same gates, same SVG finalisation, same font enforcement.

Routing is per L1 domain in `scripts/generate_mobility_wiki.py`:

```python
BACKEND_CONFIG = {code: "ollama" for code in L1_META}   # all 18 domains local
```

To route the thin air-mobility domains to a cloud model:

```python
BACKEND_CONFIG["AM"] = "openrouter"
BACKEND_CONFIG["DD"] = "openrouter"
```

```bash
export OPENROUTER_API_KEY=...
export OPENROUTER_MODEL=google/gemini-2.5-flash
```

Indicative cost for `AM` + `DD` (46 processes + 2 EA diagrams, ~200 calls, ~500K in / ~300K out):
$0.41 DeepSeek · $0.68 gpt-4.1-mini · $0.90 Gemini Flash · $2.00 Haiku 4.5 · $6.00 Sonnet 4.5.

### Secrets

Read from the environment **only** and never written to a file. `run.sh` pulls the GitHub token
from the `gh` keychain at run time:

```bash
export GITHUB_TOKEN=$(gh auth token)
```

---

## Verification

```bash
./run.sh test
```

Runs 19 sanitiser assertions and the taxonomy self-check.

Confirm no secrets were ever committed:

```bash
grep -rniE '(ghp|gho|ghs|ghu)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}' . --exclude-dir=.git
```

```bash
grep -rniE 'sk-or-v1-[A-Za-z0-9]{16,}' . --exclude-dir=.git
```

Both must return nothing.

Confirm the zoom-blur fix on any published diagram:

```bash
curl -s https://ghatk047.github.io/mobility-wiki/assets/img/ea-01.svg | grep -c 'max-width'
```

Must return `0`.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `mmdc` fails to find Chrome | `npx puppeteer browsers install chrome`, then export `PUPPETEER_EXECUTABLE_PATH` to the installed binary and persist it in your shell profile. `run.sh` auto-detects the puppeteer cache. |
| `GITHUB_TOKEN is not set` | `gh auth login`, then `export GITHUB_TOKEN=$(gh auth token)`. Note a token exported in `~/.zshrc` only resolves in **interactive** shells. |
| Diagram text renders as serif | The init block lost its top-level `fontFamily`. `finalize_svg` rewrites any remaining default declaration as a backstop. |
| Diagram blurs when zoomed | An inline `max-width` survived on the root `<svg>`. Check with the `grep -c` above; it must be `0`. |
| `REJECTED BY GATE after 3 drafts` | The local model could not produce enough rework loops or threshold-based decisions. Re-run with `--force`, or route that domain to OpenRouter. |
| Unparseable model output | Saved to `data/raw/<id>-json-<n>.txt` for inspection. |
| Pages shows an old version | `.deploy` is pushed last to trigger the rebuild; builds take 30–90s. Check `gh api repos/ghatk047/mobility-wiki/pages/builds/latest`. |

---

## Disclaimer

Independently compiled from public sources. **Not affiliated with, sponsored by, or endorsed by**
Uber, Lyft, Waymo, DoorDash, Bird, Lime, Bolt, Joby Aviation, Archer Aviation, Wisk, Zipline,
Wing, or Amazon — illustrative of mobility and micromobility industry archetypes.

Content is generated by a language model against researched registries and is intended as a
process-architecture reference, not as operational guidance or investment advice. Company status
was verified on 2026-09-09; this industry moves fast, and the registries should be re-researched
before treating any status claim as current.
