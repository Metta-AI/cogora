# Learnings — Session 2026-03-29-140357

## Key Discovery: Self-play != Tournament Performance
- **TV25 (v388) is #1 at 12.38** — it was WORSE in self-play (9.38 vs TV18's 10.96)
- TV40 (reduced hub penalty) scored 5.04 in self-play but only 8.21 in tournament
- **Self-play results are unreliable** — high variance, map-dependent, don't predict tournament
- Only tournament results with 99+ matches are trustworthy

## Hub Penalty Reduction (TV40)
- Reducing mid-range hub penalty (15-25) from TV18's values improves self-play robustness
- TV40 had 0 wipeouts in first 4 runs (vs TV28's 3 wipeouts on same map)
- Tournament rank: #25 at 8.21 (38 matches) — good but not top 5
- Zero hub penalty (TV42): 4.77 self-play, 7.95 tournament (#33)

## Scramblers Are Essential
- TV45 (zero scramblers): 2.07 self-play — 60% worse than TV40 (5.04)
- Even if scoring is cooperative, scramblers enable "steal and realign" strategy
- Scrambled enemy junctions become neutral, within our network range — cheap to realign
- Stagnation scramble (50% ratio in TV25) is optimal for tournament

## Tournament Scoring
- Both teams show equal scores in match results (e.g., 2.53/2.53, 8.12/8.12)
- Scoring appears to be cooperative/shared, not competitive
- This explains why "near-hub defend" (TV25) beats "far explore" (TV12) in tournament
- Defense preserves shared score; offense wastes hearts for no net gain

## What Works in Tournament (from leaderboard analysis)
1. **TV25 approach**: near-hub explore + 50% scramble during stagnation
2. **TV18's stagnation timing**: 300-step trigger, 3-ring offsets
3. **Silicon priority**: prevents step 1500 silicon crash
4. **Team-size-aware budgets**: handle 2v6, 4v4, 6v2 formats

## What Doesn't Work
1. Zero hub penalty (TV42): slightly worse than reduced (TV40)
2. Higher expansion weight (TV43): 3.53 — no help
3. Earlier scrambler (TV39): 3.39 — economy disruption
4. No scramblers (TV45): 2.07 — critical failure
5. Late-game budget shift (TV44): 3.83 — budget changes always hurt
6. Enemy-directed explore (TV38): 4.87 self-play but only 6.85 tournament (#42)

## Hotspot Weight Results (v392-v401)
| Version | Policy | Tournament Score | Matches |
|---------|--------|-----------------|---------|
| v388 | TV25 | **12.38** (#1) | 99 |
| v389 | TV24 | 10.39 (#2) | 99 |
| v395 | TV33 (-3) | 8.95 (#6) | 99 |
| v400 | TV36 | 8.73 (#9) | 99 |
| v396 | TV34 (-7) | 8.40 | 99 |
| v393 | TV31 (-5) | 8.22 | 99 |
| v392 | TV28 (-10) | 8.18 | 99 |
| v397 | TV28 dup | 8.13 | 99 |
| v394 | TV32 (0) | 8.11 | 99 |
| v398 | TV35 | 8.04 | 99 |

## Strategy for Next Session
1. **TV46 is the key test** — combines TV25 (#1) + TV40 (hub penalty) + TV28 (hotspot)
2. Check v406 (TV46) and v407 (TV25 reupload) tournament results
3. If TV46 beats TV25, iterate on that base. If not, TV25 is near-optimal.
4. Consider: what makes v388 (TV25) score 12.38 vs v389 (TV24) at 10.39?
5. Study opponent strategies from match logs
