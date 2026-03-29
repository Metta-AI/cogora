# Learnings — Session 2026-03-29-150452

## Key Discovery: Lower Scramble Threshold Wins
- **v410 (TV50) is NEW #1 at 12.69** (48 matches) — beating v388's 12.38!
- TV50's only change: lower min_res threshold for scrambling (7 vs 14)
- This lets idle aligners scramble earlier when economy is tighter
- The simplest change produced the best result

## Scramble Ratio Experiments
| Policy | Self-play 5K | Tournament Score | Tournament Rank |
|--------|-------------|-----------------|-----------------|
| TV25 (baseline, 50% scramble) | 2.98 | 12.38 (99m) | #3 |
| TV47 (earlier stagnation) | 4.99 | 12.03 (49m) | #5 |
| TV48 (70% scramble) | 6.60 | 11.75 (53m) | #9 |
| TV49 (100% scramble) | 4.34 | 9.05 (28m) | — |
| TV50 (lower threshold) | 4.84 | **12.69** (48m) | **#1** |
| TV51 (70% + earlier stag) | 7.43 | 11.79 (51m) | #8 |
| TV52 (dedicated scrambler) | 3.34 | 8.59 (28m) | — |
| TV53 (TV46 + TV48) | 4.33 | **12.57** (49m) | **#2** |
| TV54 (TV46 + TV51) | 1.41 | 11.95 (49m) | #7 |

## Self-play vs Tournament: Confirmed Unreliable
- TV51 = best self-play (7.43) but only #8 in tournament (11.79)
- TV50 = mediocre self-play (4.84) but #1 in tournament (12.69)!
- TV54 = worst self-play (1.41) but #7 in tournament (11.95)
- **Self-play is useful for catching disasters but NOT for predicting tournament rank**

## What Works in Tournament
1. **Lower scramble threshold (TV50)**: min_res >= 7 vs 14 → more consistent scrambling
2. **TV46 targeting + 70% scramble (TV53)**: reduced hub penalty + more stagnation scramble
3. **Original TV25 is near-optimal**: hard to beat significantly

## What Doesn't Work
1. **Dedicated scramblers (TV52)**: 8.59 — trading an aligner for scrambler hurts
2. **100% scramble during stagnation (TV49)**: 9.05 — too aggressive
3. **Higher scramble ratio alone (TV48)**: 11.75 — doesn't translate to tournament
4. **70% scramble + earlier stagnation (TV51)**: 11.79 — combining both is worse

## Interesting Pattern
- Changes that affect stagnation scramble TIMING matter less than THRESHOLD
- TV50 (lower threshold) wins because it enables scrambling MORE OFTEN, not more intensely
- TV48 (higher ratio) increases intensity but not frequency → less effective

## Strategy for Next Session
1. Wait for v410 and v414 to reach 99 matches for definitive ranking
2. Try intermediate thresholds: min_res >= 10, min_res >= 5
3. Consider combining TV50's threshold with TV46's targeting
4. Study opponent logs from v410 matches to understand dynamics
