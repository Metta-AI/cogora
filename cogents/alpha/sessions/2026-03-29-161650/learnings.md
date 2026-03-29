# Learnings — Session 2026-03-29-161650

## Key Finding: v414 and v410 are Near-Optimal
- v414 (TV53 = TV46 targeting + 70% scramble) = 12.63 remains #1 at 99m
- v410 (TV50 = lower scramble threshold 7) = 12.59 remains #2 at 99m
- No new variant this session significantly beat them

## Combination Effects are Not Additive
- TV55 (TV46+TV50): 12.42 at 51m — combining doesn't beat either parent
- TV58 (TV46+TV50+70%): 12.53 at 48m — slightly better, still below v414
- TV57 (TV50+70%): 11.64 — combining these two hurts
- Adding improvements together doesn't produce additive gains

## Scramble Ratio Sensitivity
| Scramble % | Policy | Score (50+m) |
|-----------|--------|-------------|
| 50% (base) | TV25 (v388) | 12.38 |
| 70% | TV53 (v414) | 12.63 |
| 70% + thresh=7 | TV58 (v419) | 12.53 |
| 80% | TV61 (v422) | 11.65 |
| 80% optimal is somewhere between 50-80%, likely 60-70%

## Scramble Threshold Sensitivity
| Threshold | Policy | Score (50+m) |
|-----------|--------|-------------|
| 3 | TV56 (v417) | 12.01 |
| 7 | TV50 (v410) | 12.59 |
| 10 | TV60 (v421) | 12.52 |
| 14 | TV25 (v388) | 12.38 |
- Threshold=7 is optimal
- Threshold=10 surprisingly close (12.52 vs 12.59)
- Threshold=3 too aggressive but not catastrophic

## Earlier Stagnation Trigger
- TV62 (200 steps) = 11.10 — significantly worse than TV25's 300 steps
- Earlier stagnation detection is harmful — false positives cause premature scrambling

## Aggressive 2-Agent Play
- TV59 (TV55 + 2-agent aggression) = 12.40 vs TV55's 12.42
- No meaningful improvement from earlier 2-agent alignment

## TV46 Targeting Value
- TV46's reduced hub penalty adds measurable value in TV53 (+0.25 over TV25)
- But combining it with TV50 threshold (TV55) doesn't produce the same additive gain
- The targeting improvement and threshold improvement may optimize the same pathway

## Self-Play Reliability
- Self-play continues to be anti-correlated with tournament
- TV55 self-play 5.22 → tournament 12.42
- TV56 self-play 4.22 → tournament 12.01
- Self-play is only useful for catching obvious bugs (score near 0)

## Strategy for Next Session
1. v414 (12.63) and v410 (12.59) are near the ceiling for this approach
2. Need fundamentally different strategy to break past 12.6
3. Possible directions:
   - Completely different role allocation (more aligners?)
   - Defensive scrambling (protect our junctions instead of attacking)
   - Better junction targeting (chain-building priority)
   - Faster initial expansion (align more junctions in first 500 steps)
4. v425 (TV64, always-scramble) and v426 (TV65, delayed economy) may provide data
