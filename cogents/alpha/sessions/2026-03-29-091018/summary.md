# Session 2026-03-29-091018 Summary

Extensive policy experimentation session. Tested 8+ variants across
chain push, burst exploration, tournament budget caps, silicon priority,
and adaptive partner response.

## Key Results
- **v368 (TV12) is #1 at 8.69** — stagnation detection works
- Chain push (TV11): neutral on average, increases variance
- Budget caps (TV16, v372): 6.59 — MUCH worse, don't change budgets
- Silicon priority (TV14, v370): 8.15 — also worse
- Self-play vs tournament gap: 32% (12.87 vs 8.69)

## Uploads
v370, v371, v372, v376, v378 — none beat v368 (8.69)

## Critical Learning
Tournament performance ≠ self-play performance.
TV12's AdaptiveV3 budgets are near-optimal.
Only add non-disruptive improvements to TV12 base.
