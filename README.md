# Mobility & Micromobility Process Wiki

A homogeneous business-process taxonomy spanning six mobility operating models that share a
marketplace and dispatch core: ride-hail, autonomous ride-hail, last-mile delivery,
micromobility, eVTOL air mobility and drone delivery.

**357 processes / 18 L1 domains / 74 L2 process groups**, in three tiers:

| Tier | Scope | Domains | Processes |
|---|---|---|---|
| 1 | Shared marketplace core | 6 | 122 |
| 2 | Archetype-specific operations | 5 | 120 |
| 3 | Cross-cutting enterprise | 7 | 115 |

Live: https://ghatk047.github.io/mobility-wiki/

## Sourcing

Every process is generated against `registries/*.json` — a set of researched, verified facts
with sources, not model recall. Where public sourcing is genuinely thin (Waymo's production
autonomy stack, eVTOL operational procedure, drone operators' internal orchestration) pages
are marked **sparse** and the EA diagram renders those nodes dashed, rather than inventing
product names to fill the gap.

## Running

```bash
export GITHUB_TOKEN=$(gh auth token)
python3 scripts/generate_mobility_wiki.py --bootstrap
python3 scripts/generate_mobility_ea.py --id ea-01
python3 scripts/generate_mobility_wiki.py --pid MM-MD-DM-01
python3 scripts/test_sanitiser.py
```

Secrets are read from the environment only and never written to a file.

---
Independently compiled from public sources. Not affiliated with, sponsored by, or endorsed by
Uber, Lyft, Waymo, DoorDash, Bird, Lime, Bolt, Joby Aviation, Archer Aviation, Wisk, Zipline,
Wing, or Amazon — illustrative of mobility and micromobility industry archetypes.
