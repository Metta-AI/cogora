# Learnings — 2026-03-30-141102

## Best Innovation: Bottleneck Scramble (TV305/v667)

**v667 avg 16.83 across 4 matches** (all internal: vs v11 and v557)
- 4v4 vs v557: 16.71
- 4v4 vs v11: 17.27
- 2+6 vs v11: 16.57
- 6+2 vs v11: 16.77

The bottleneck scramble targets the enemy junction that blocks the MOST neutral
junctions from being aligned. During stagnation, instead of scrambling random
enemy junctions, it finds the one whose removal would unblock the most
alignment opportunities.

## What Worked

1. **Bottleneck scramble (TV305)**: 17.27 in 4v4 — far above v637's 14.88 ceiling.
   The key insight: when stagnating, scramble strategically, not randomly.

2. **2-level expansion lookahead (TV302)**: 56% improvement in local self-play
   (7.94 vs 5.09). Tournament avg 12.84 across 12 matches (dragged down by weak partners).
   Internal matchups: 14.02-14.21 — similar to v637.

3. **Re-align bonus (TV308 negative hotspot)**: 16.77 in 6+2 vs v11. Helps recover
   from scramble events.

4. **Conservative 4-agent economy (TV312)**: avg 13.11 vs Paz-Bot (3m). Prevents
   the economy crash at step 2000 that plagued 4v4 matches.

## What Failed or Was Neutral

1. **2-level lookahead + bottleneck (TV306/v668)**: 14.02 in 4v4 vs v11 — adding
   lookahead to bottleneck HURT (14.02 vs 17.27). The lookahead may change junction
   targeting in a way that interferes with the bottleneck scramble strategy.

2. **Zone-based alignment (TV303/v665)**: 13.50 in 4v4 vs v13. Decent but not
   better than baseline.

3. **Carbon-weighted bias (TV313/v675)**: 9.63 in 4v4 vs Paz-Bot. Not helpful.

4. **TV318 (2-level + re-align + carbon)**: 5.69 in 4v4 vs Paz-Bot. Terrible.
   Kitchen sink combos tend to degrade 4v4 performance.

5. **Higher expansion weight (TV310)**: Neutral to slightly negative.

## Key Insights

1. **Single innovations beat combos**: TV305 alone (17.27) > TV306 combo (14.02).
   This pattern has appeared before — combining changes often cancels benefits.

2. **4v4 is the critical config**: It's where most variation appears. 2+6 and
   6+2 scores tend to cluster around 14-16 regardless of strategy.

3. **Local self-play != tournament**: TV302 was 56% better locally but only
   matched TV277 in tournament internal matches. Tournament dynamics are different
   (16 cogs vs 8 in local).

4. **Economy crashes are a 4-agent problem**: With only 4 agents, 2 miners can't
   sustain 2 aligners. Conservative budgets (TV312) help.

5. **Weak partners dominate score variance**: vs gtlm-reactive/coglet we score
   7-12; vs our own strong versions we score 14-17. Partner quality matters more
   than our strategy refinements.

## Variants Created (TV302-TV321)

| TV  | Version | Concept | Best 4v4 Score |
|-----|---------|---------|----------------|
| 302 | v664 | 2-level expansion lookahead | 14.02 (vs v17) |
| 303 | v665 | Zone-based aligner assignment | 13.50 (vs v13) |
| 304 | v666 | TV302 + TV303 combined | ? |
| 305 | v667 | **Bottleneck scramble** | **17.27 (vs v11)** |
| 306 | v668 | TV302 + TV305 | 14.02 (vs v11) |
| 307 | v669 | Late-game all-aligner | 10.60 (vs slanky) |
| 308 | v670 | Re-align bonus (neg hotspot) | ? (16.77 in 6+2) |
| 309 | v671 | TV302 + all-aligner + re-align | 12.76 (vs v13) |
| 310 | v672 | Higher expansion weight | 9.33 (vs coglet) |
| 311 | v673 | Lower network weight | ? |
| 312 | v674 | Conservative 4-agent economy | 11.42 (vs Paz-Bot) |
| 313 | v675 | Carbon-weighted bias | 9.63 (vs Paz-Bot) |
| 314 | v676 | TV312 + TV302 | 11.50 (vs Paz-Bot) |
| 315 | v677 | Lower deposit threshold | ? |
| 316 | v678 | Early aligner rush (500 steps) | ? |
| 317 | v679 | Short rush (200 steps) | ? |
| 318 | v680 | TV302 + TV308 + TV313 | 5.69 (vs Paz-Bot) |
| 319 | v681 | TV305 + TV308 | ? (awaiting) |
| 320 | v682 | TV305 + TV312 | ? (awaiting) |
| 321 | v683 | TV305 + TV308 + TV312 | ? (awaiting) |

## Next Steps

1. Monitor v667 (TV305) as it accumulates more matches, especially vs external opponents.
2. Monitor v681-v683 (combinations with TV305) to see if combos help or hurt.
3. If TV305 holds up, create more variants around the bottleneck scramble idea:
   - Different bottleneck thresholds (require 3+ blocked neutrals instead of 2)
   - Bottleneck scramble even when NOT in stagnation mode
   - Earlier stagnation detection to trigger bottleneck sooner
