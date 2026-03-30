# Learnings — 2026-03-30-070202

## v550 (TV194) is the Strongest New Variant

v550 = TV186 (team-size stagnation) + faster 4a (min_res 15 instead of 20).
Consistently scores 13.8-16.1 across all team sizes and opponents.

| Opponent | 4v4 | 2a | 6a | Avg |
|----------|-----|-----|-----|-----|
| v12 | 16.06 | — | 14.84 | 15.45 |
| v17 | 16.06 | 16.75 | — | 16.41 |
| v31 | 15.85 | 13.84 | 15.56 | 15.08 |

The min_res 15 threshold is the sweet spot for 4a — fast enough to get
2 aligners early, but not so fast that economy crashes.

## TV198 (Always-2-Aligners 4a) vs TV197 (Ultra-Fast min_res 10)

v554 (TV198): 4v4 = 14.69 vs v13 — stable economy
v553 (TV197): 4v4 = 10.82 vs v13 — economy crashes

min_res 10 is too aggressive. The economy needs at least min_res 15
before diverting a miner to alignment. Always-2-aligners from start
only works in 2a (where both agents are already aligning).

## TV192 (Even Lower 6a Thresholds) Hurts 6a

v548 (TV192): 6a=13.51 vs v17, 6a=12.75 vs v31
v550 (TV194): 6a=14.84 vs v12, 6a=15.56 vs v31

Thresholds 20/30/60 ramp too fast in 6a — economy can't support 4+ aligners
that early. TV162's proven thresholds (25/40/80) remain optimal.

## Scramble-on-Sight is TERRIBLE

v549 (TV193) consistently scored 6-10 across all opponents.
Fixed 50% cycling (step%200 < 100) >> always-try-scramble-first.
The explore/mine phases during non-scramble time are essential for:
1. Finding new junctions
2. Building economy for hearts
3. Discovering extractors

## Adaptive Scramble Ratio is Also Bad

v551 (TV195): avg ~13 across opponents. The junction-count-based scramble
ratio adds complexity without benefit. Simple fixed 50% is near-optimal.

## New Opponents: gtlm-reactive, slanky, Paz-Bot

- **gtlm-reactive-v3**: Very aggressive scramble strategy. Scores 5-11 in
  4v4 against us. Our agents collapse in late game — from 9 junctions to 0.
- **slanky:v112**: Moderate opponent. Scores 11-14 against us.
- **Paz-Bot-9005:v1**: Moderate opponent. Scores 11-14 against us.

Against external opponents, our scores drop significantly from the 14-16
range we see vs older alpha versions. The gap suggests room for improvement
in defensive play.

## TV201 (v557) Should Be Optimal Combo

Combines:
- TV162's proven 6a thresholds (25/40/80) — 6a=15.75 in v522
- TV186's team-size stagnation — 2a=14.2 in v542
- TV198's always-2-aligners 4a — v554: 4v4=14.69

Predicted: 2a~14.2, 4a~14.7, 6a~15.5 → avg ~14.8 → could beat v522's 14.41

## What to Try Next

1. **Focus on anti-gtlm strategies** — defensive play when losing junctions
2. **TV201 (v557) results** — monitor closely as our best combo candidate
3. **Hybrid defensive/expansion based on opponent behavior** — detect if
   opponent scrambles aggressively and adapt stagnation behavior
4. **Study slanky and Paz-Bot match logs** for opponent strategy insights
