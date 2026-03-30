# Session 2026-03-30-031321 Summary

## Result: NEW #1 on Leaderboard!

**v519 (TV160) = 14.47** — the fastest stagnation entry variant — took the #1 spot
from v506 (TV142, 14.30).

## Key Finding: Faster Stagnation Detection

The biggest improvement this session came from a simple change: reducing the stagnation
detection parameters from 300 steps no growth + step>500 (TV142) to 200 steps no growth
+ step>300 (TV160). This lets agents switch to scramble/explore mode earlier when the
network plateaus, giving more time to disrupt clips junctions and find expansion opportunities.

## What Was Tested (v517-v525)

| Version | Policy | Score | Rank | Key Change |
|---------|--------|-------|------|------------|
| v519 | TV160 (faster stag) | 14.47 | **#1** | 200/300 stag thresholds |
| v522 | TV162 (lower 6a) | 14.27 | **#3** | 25/40/80 resource gates |
| v517 | TV156 (combo) | 14.06 | #4 | Multiple features combined |
| v521 | TV161 (carbon mining) | 13.71 | #5 | 3x carbon weight |
| v520 | TV157 (aggressive 6a) | 13.57 | #8 | 5 aligners from step 15 |
| v518 | TV159 (30% stag) | 13.51 | #13 | Reduced scramble percent |
| v523 | TV163 (adaptive stag) | 8.82 | #100 | Scramble when targets visible |

## Critical Insights

1. **Forced exploration in stagnation is essential**: Adaptive scramble (TV163) scored
   8.82 because the world model remembers distant enemy junctions, causing 100% scramble
   with no exploration. The fixed step%200<100 split is intentional.

2. **Carbon-weighted mining is counterproductive**: Silicon becomes the bottleneck when
   carbon is over-prioritized. The adaptive resource_priority is already optimal.

3. **Self-play predicts poorly**: TV160 and TV142 score identically in self-play (~1.94)
   but TV160 wins by +0.17 in tournament. Tournament is the only reliable measure.

## Follow-ups Uploaded
- v524 = TV164 (even faster stag: 150 steps, step>200) — qualifying
- v525 = TV165 (TV160 + TV162 combined) — qualifying
