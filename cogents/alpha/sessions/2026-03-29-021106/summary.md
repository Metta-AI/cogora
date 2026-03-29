# Session 2026-03-29-021106 Summary

## Goal
Score >10 in CogsVsClips tournament. Previous best: v290 at 6.84 avg.

## Key Results
- **AlphaAllCarbonPolicy avg 8.13 on 8a (4v4)** — best local result (7.84, 9.35, 7.20 across 3 seeds)
- Identified carbon depletion as #1 bottleneck (3x consumed by aligner gear)
- Carbon-biased mining prevents death spirals on bad seeds
- TeamFix (num_agents correction) HURTS 4v4 — the "bug" gives better budgets
- Scramblers are essential (no-scramble variants score 0-1.38)
- Corrected test format understanding: `-c 8` = 4v4 = main tournament format

## Policies Uploaded
- v328=CarbonBoost (50% carbon), v329=Aggressive, v330=Focused
- v333=TeamFix, v334=TeamCarbon, v335=SmartHybrid(buggy), v336=SmartHybrid(fixed)
- v338=AllCarbon (best) — **100% carbon bias + Aggressive budgets**

## Score Comparison (8a = 4v4 tournament format)
| Policy | Seed 1 | Seed 42 | Seed 123 | Avg |
|--------|--------|---------|----------|-----|
| AllCarbon | 7.84 | 9.35 | 7.20 | **8.13** |
| CarbonBoost | 5.89 | 9.35 | — | 7.62 |
| Aggressive | 6.31 | 0.00 | — | 3.15 |
| TeamFix | — | 1.72 | — | 1.72 |

## Status
- Tournament matches still running at session end (no completed results)
- v338 (AllCarbon) is the best policy to track
- Goal >10 not yet achieved; avg 8.13 locally, need ~25% more improvement
