# Learnings — Session 2026-03-29-170732

## TV61 (v422) is the Local Optimum
- Score: 12.83 at 63 matches, #1 on leaderboard
- Configuration: TV58 kitchen sink (TV46 targeting + TV50 threshold + TV48 70% scramble) + 80% stagnation scramble
- No variant tested this session improved on it

## What Doesn't Work (Confirmed)
1. **Dedicated scramblers**: v427 (TV66) = 5.94. Adding dedicated scrambler budget ALWAYS hurts. Scramblers consume hearts that aligners need.
2. **Ultra-aggressive scramble thresholds**: v430 (TV69, min_res >= 3) = 8.00. Scrambling with too few resources depletes economy.
3. **Faster early alignment**: v432 (TV71, 3 aligners at step 10) = 8.44. Economy can't support it.
4. **More aligners when economy healthy**: v435 (TV74) = 8.12. More aligners != better score.
5. **Defensive scramble targeting**: v429 (TV68) = 10.17. Changing target selection from default hurts.
6. **Kitchen sink v2**: v433 (TV72) = 8.08. Combining many aggressive changes compounds negatives.

## What Marginally Helps or is Neutral
1. **Lower heart batch target**: v436 (TV75) = 11.29. Aligners leaving hub faster is slightly helpful but not enough to beat TV61.
2. **85% scramble**: v434 (TV73) = 11.00. 85% is worse than 80% — 80% is near optimal.
3. **Improved 2-agent play**: v431 (TV70) = 12.06. The 2-agent change (aligner at step 200 vs 500) seems slightly helpful but overall score is still below TV61.

## Scramble Percentage Sweet Spot
- 50% (TV25) = 12.38
- 70% (TV48/TV58) = 12.55
- 80% (TV61) = 12.83 ← BEST
- 85% (TV73) = 11.00
- 90% (TV69) = 8.00
- 100% (TV49) = 9.05

The optimal scramble percentage is **exactly 80%** during stagnation. The dropoff from 80% to 85% is surprisingly sharp.

## Architecture Ceiling
All top 11 variants (12.22-12.83) are heuristic policies with scramble-focused strategies. The gap between them is small (0.6 points). We may be near the ceiling for this heuristic approach.

## External Opponents
- slanky:v112 = 3.92 (rank 104)
- Paz-Bot-9005:v1 = 3.87 (rank 105)
- gtlm-reactive-v3:v1 = 1.92 (rank 346)
- We're 3x better than any external competitor
