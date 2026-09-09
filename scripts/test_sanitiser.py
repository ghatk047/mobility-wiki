#!/usr/bin/env python3
"""
test_sanitiser.py — proves the two properties that are in tension in sanitise_mermaid().

Any regex that rewrites digit-leading node IDs (`1.1` -> `S1_1`) will also mangle a
real regulatory citation (`FAA Part 107.31`, `ASTM F3548-21`, `CPUC Decision 18-05-043`)
unless label text is stashed and restored around that step. This file asserts BOTH:

  1. real citations inside labels survive byte-for-byte
  2. real digit-leading node IDs outside labels still get fixed

Run:  python3 scripts/test_sanitiser.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_mobility_wiki import sanitise_mermaid, INIT_LINE, FONT_STACK  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f"  — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


# ── Fixture: citations in every label shape, plus digit-leading node IDs ──────
SRC = """```mermaid
---
title: should be stripped
---
%%{init: {'theme':'dark','themeVariables':{'fontSize':'40px'}}}%%
flowchart LR
  subgraph P1[Phase 1: Authorisation]
    1.1([Start]) --> 1.2[File BVLOS waiver under FAA Part 107.31<br/>FAA DroneZone portal]
    1.2 --> 1.3{Waiver granted under<br/>14 CFR Part 108 proposed?}
    1.3 -- No --> 1.2
    1.3 -- Yes --> 2.1[Register USS under ASTM F3548-21\\nStrategic Coordination role]
  end
  subgraph P2[Phase 2: Deployment]
    2.1 --> 2.2[Confirm CPUC Decision 18-05-043 authority\\nCPUC TLAB filing]
    2.2 --> 2.3{Prop 22 earnings floor met?}
    2.3 -- No --> 2.2
    2.3 -- Yes --> 2.4([End])
  end
  2.2 --gt; 2.3
  style 1.1 fill:#0f2a5c,color:#fff
"""

OUT = sanitise_mermaid(SRC)

print("=" * 74)
print("SANITISER TEST — citation survival vs digit-leading node ID rewriting")
print("=" * 74)

print("\n1. Real citations must survive INSIDE labels, byte-for-byte:")
CITATIONS = [
    "FAA Part 107.31",           # square-bracket label
    "14 CFR Part 108",           # curly decision diamond
    "ASTM F3548-21",             # hyphenated standard
    "CPUC Decision 18-05-043",   # multi-hyphen decision number
    "Prop 22",                   # bare number in a diamond
]
for c in CITATIONS:
    check(f"{c!r} intact", c in OUT,
          f"got: ...{OUT[max(0, OUT.find(c.split()[0]) - 20):][:70]}...")

print("\n2. Real digit-leading node IDs must STILL be rewritten:")
check("node ID 1.1 -> S1_1", "S1_1" in OUT and "1.1(" not in OUT)
check("node ID 2.1 -> S2_1", "S2_1" in OUT)
check("no bare digit-leading ID survives before a shape token",
      not any(f"\n  {n}[" in OUT or f"\n  {n}(" in OUT or f"\n  {n}{{" in OUT
              for n in ("1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "2.4")))
check("style line target rewritten too", "style S1_1" in OUT)

print("\n3. Structural cleanups:")
check("markdown fence stripped", "```" not in OUT)
check("YAML frontmatter removed", "title: should be stripped" not in OUT)
check("<br/> converted to literal backslash-n", "<br/>" not in OUT)
check("HTML-encoded arrow --gt; fixed", "--gt;" not in OUT and OUT.count("-->") >= 8)
check("model init block replaced, not appended", OUT.count("%%{init") == 1)
check("canonical init is line 1", OUT.split("\n")[0] == INIT_LINE)
check("model's 40px fontSize discarded", "40px" not in OUT)
check("canonical font stack forced", FONT_STACK in OUT)
check("no blank line between init and flowchart",
      OUT.split("\n")[1].strip().startswith("flowchart"))

print("\n4. Label character cleaning:")
check("parentheses stripped from inside labels",
      "(" not in OUT.split("classDef")[0].replace("([", "").replace("])", ""))

print("\n" + "-" * 74)
print("SANITISED OUTPUT:")
print("-" * 74)
print(OUT)
print("-" * 74)

if FAILURES:
    print(f"\n{len(FAILURES)} FAILURE(S): {', '.join(FAILURES)}")
    sys.exit(1)
print("\nAll sanitiser assertions passed.")
