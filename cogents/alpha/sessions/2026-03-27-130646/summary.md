# Session Summary: 2026-03-27-130646 (Interrupted)

## Key Achievements
- Uploaded v39-v43 with incremental improvements
- Hub proximity bias: junctions >25 from hub get 1.5x penalty
- Scramble detection threshold lowered to 1 (faster detection)
- Average score improved from ~1.5 to ~2.3 (50% improvement)
- v42 best local avg: 2.55 across 3x 10k runs

## Key Learnings
- Hub proximity is a strong scoring factor (closer junctions more valuable)
- Fast scramble detection (threshold=1) significantly helps
- Map-dependent variance is the #1 challenge
- Occasional 0.00 wipeouts on bad map seeds persist
