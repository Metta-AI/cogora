# Session Summary — 2026-03-31-071539

## Goal
Improve competition score from v912 avg 1.93 toward target of >10.

## Analysis
- Analyzed match logs: 6v2 vs mammet (0.64) and 4v4 vs slanky (5.32)
- Root cause: economy collapse (resource→0, hearts→0, territory cascade)
- 67% of time with hearts=0, only 12.6% time contesting territory

## Changes Made
1. **Territory-responsive scrambler scaling** (v914/v915) — shift budget toward scramblers when losing territory
2. **Early-game aggression** (v916) — extra pressure agent first 500 steps
3. **Mining resource balance** (v917) — raise threshold 7→21 to prevent bottleneck crashes
4. **6v2 regression fix** (v918/v919) — don't shift to scramblers when majority team
5. **Scoring optimizations** (v920) — network_weight=0, hotspot re-alignment bonus
6. **AlphaTournament base** (v921/v922) — upload proven v884 policy with mining fix

## Results
- v915 competition avg: 1.37 (13 matches) — slight regression from v912's 1.93
  - Improvements: mammet 6v2 +22%, coglet 4v4 +56%
  - Regression: 6v2 matchups due to premature scrambler shift (fixed in v918)
- v921 (AlphaTournament): 0.75 vs mammet, 2.07 vs slanky — not the expected 9.58
- v919, v921, v922 all in competition with matches running

## Key Finding
Historical v884 avg 9.58 was against easier opponent pool. Current opponents (mammet v13, modular-lstm v13) are much harder. Heuristic ceiling against strong opponents is ~2-3.
