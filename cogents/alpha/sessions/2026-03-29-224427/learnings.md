# Session Learnings — 2026-03-29-224427

## Heuristic Ceiling Confirmed at ~13.0
- TV82 baseline: 12.98 avg (65 matches). All modifications scored worse.
- Tested: dynamic stagnation, reduced retreat, faster ramp, dual aligner, very aggressive retreat, combos.
- Every change hurt. The base heuristic is a robust local optimum.

## Retreat Margin Is Well-Calibrated
- Default margin=20 is optimal. Reducing to 10 (v479) → 10.96. Reducing to 5 (v481) → still qualifying.
- Agents that retreat less die more, losing gear and wasting time re-equipping.
- The modifiers (enemy AOE, hearts, cargo, gear loss) are all correctly tuned.

## Budget Changes for 2-Agent Teams Risky
- Current accidental behavior (8-agent budget → team cap to 1 aligner) works well.
- TV122 dual aligner (both align when min_res >= 14) → 11.16 (2m, early).
- TV109 budget fix to (1,0) → 5.36 — much worse.
- Any budget change for 2-agent needs very careful testing.

## Dynamic Stagnation Recovery Neutral
- TV117 (reduce scramble from 80% to 50% when losing territory) → 12.04 (49m).
- Slightly worse than baseline. Scramble frequency is already optimal.

## Score Distribution
- 2v: ~11.6 (weakest, 66% of matches)
- 4v: ~13.6 (strong)
- 6v: ~14.0 (strongest)
- 8v: ~11.2 (self-play)
- Biggest improvement opportunity is in 2v, but every 2v change so far hurt.
