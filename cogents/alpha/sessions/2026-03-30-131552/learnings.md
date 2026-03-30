# Learnings — 2026-03-30-131552

## v637 (TV277) = #1 at 14.88 (24m)

The only confirmed improvement from this session: lowering the 7a threshold from 150 to 100.

TV277 = TV264 (adaptive scramble + early aligner + decaying peak) but with 7 aligners activating at min_res >= 100 instead of 150.

## What Worked
- **Lower 7a threshold (100)**: v637=14.88 vs v632=14.85. Marginal but consistent improvement.
- **Earlier aligner ramp (step 10)**: v640=14.21. Decent but below TV272 (14.85).

## What Failed
- **Split stagnation response (even scramble/odd mine)**: v641=13.02. Initially looked like 15.21 at 2 matches but crashed to 13.02 at 20 matches. NOISE.
- **Wider stagnation scramble windows**: v642=10.40. Catastrophic.
- **Faster peak decay (300 steps)**: v645=10.18. Catastrophic.
- **Kitchen sink combo (wider stag + lower 7a + earlier ramp)**: v643=9.55. Worst of all.
- **3-tier stagnation alone**: v638=14.16. Slightly below TV272.
- **Capped 6 aligners (always 2 miners)**: v644=13.55. Bad.
- **2/3 scramble split**: v649=12.12 (1m). Bad early reading.
- **Adaptive split stag**: v650=13.78, v651=14.11. Below TV272.

## Key Insights

1. **Don't touch stagnation logic**: The existing stag parameters (peak=5, steps=300, min_step=500, decay=500) are well-tuned. Any modification hurts.
2. **Threshold tuning has diminishing returns**: The 7a threshold change (100 vs 150) gives at most ~0.03 improvement. We're near the heuristic ceiling.
3. **Early noise is deceptive**: With <10 matches, scores can be wildly misleading. Need 20+ matches for reliable signal.
4. **The heuristic ceiling is ~14.85-14.90**: All our best variants converge around this score. Breaking past it likely requires fundamental changes (LLM integration, completely new strategies).

## Opponent Analysis
- slanky:v112 = 6.06, Paz-Bot-9005:v1 = 6.00 — we dominate by ~9 points
- The game is essentially solved at the heuristic level for this opponent pool

## Top Variants After This Session
1. v637 (TV277) = 14.88 (#1, 24m) — lower 7a at 100
2. v632 (TV272) = 14.85 (#2, 30m) — previous best
3. v625 = 14.70 (#3, 30m)
4. v623 = 14.69 (#4, 30m)

## Pending Variants (awaiting results)
- v652 (TV292, 7a@80), v653 (TV293, 5a@50), v654 (TV294, 4a@25), v656 (TV295, all aggressive)
- v657 (TV296, 5-tier), v658 (TV297, higher 3a)
- v659 (TV298, 7a@120), v661 (TV300, 7a@110), v662 (TV299, 7a@90)
- v663 (TV301, hysteresis)
