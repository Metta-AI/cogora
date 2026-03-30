# Session Summary — 2026-03-30-091114

## One-line Summary
18 new variants tested (TV210-TV227), v564 (TV208) confirmed as stable #1 at ~15.0

## What Happened
1. Recovered crashed session 082457 (8 variants v558-v565 uploaded)
2. Checked leaderboard — v558-v565 scoring 15-16+ (inflated by v557 opponents)
3. Created TV210-TV214: 4a optimizations on TV209 base → v566-v570
4. Created TV215-TV218: stagnation modifications → v571-v574
5. Created TV219-TV220: combo variants → v575-v576
6. Created TV221-TV227: 6a-focused variants on TV208 base → v577-v583
7. Monitored convergence as scores dropped from 16+ to 14.5-15.0

## Key Findings
- **TV208 (v564) is the optimal policy**: 6a thresholds 22/35/70 + 3-tier stagnation
- **Stagnation modifications are catastrophic**: All scored 9-14 (below baseline 14.69)
- **4a aggressive changes hurt**: Full combo (TV212) dropped to 14.55 vs TV208's 14.96
- **Early scores are unreliable**: Need 15-20 matches, 3-match scores off by 2-3 points
- **Heuristic ceiling is ~15.0**: TV208 at 14.96, theoretical max ~32

## Status at Session End
- v564 (TV208) = #1 at 14.96 (18m) — stable
- v566 (TV210) = #2 at 15.09 (18m) — slightly higher but within noise
- Goal of >10 achieved (14.96 at stable convergence)
- 18 new variants uploaded this session (v566-v583)
