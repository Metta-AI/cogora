# Learnings — Session 2026-03-31-002058

## Key Breakthrough: Faster Stagnation Detection for 2-Agent Games
- **v873 (TV478) avg 10.13** — first variant to consistently exceed goal >10 in competition across diverse matchups.
- The key innovation: faster stagnation detection for 2 agents: `peak=2, stag_steps=150, min_step=200` (vs TV350's `peak=3, stag_steps=200, min_step=300`).
- Plus lower scramble resource threshold: `min_res >= 3` (vs 7) for 2 agents.
- This means the policy enters scramble mode much earlier when territory is lost, disrupting enemy expansion.

## "Always 2 Aligners" Works With Faster Stagnation
- TV477 (always 2 aligners for 2 agents, budget 2,0) HURTS without faster stagnation: v872 scored 0.31 in 2v6 vs modular-lstm.
- But TV478 (always 2 aligners + faster stagnation) = 8-12 in 2v6. The faster stagnation compensates.
- **Why**: With (2,0) budget, BOTH agents can scramble during stagnation. With (1,0), only the aligner can scramble while the miner mines. 2x scramble pressure = better territory recovery.

## TV350 Budget + Faster Stagnation = Worse Than Expected
- v877 (TV481) tested TV350 budget (1,0 when low) + faster stagnation: avg 8.56 < v873's 10.13.
- The dedicated miner can't participate in scramble, reducing effectiveness by ~50%.

## Capture-Optimized Scramble Hurts 6v2
- v870 (TV475 capture scramble) scored 5.87/6.09 in 6v2 (should be 14+).
- Don't change scramble targeting for 6v2 — TV350's base scramble works fine.

## Modular-LSTM Incredibly Strong
- Even with 2 agents, modular-lstm beats our 6 agents (v874 6v2 scored 2.82).
- 4v4 vs modular-lstm: consistently 0-4 (terrible).
- RL-trained policies are fundamentally better. Need RL training (GPU) to compete.

## Competition Score Distribution
- 6v2 matchups: 7-16 (good, our strength)
- 4v4 matchups: 5-12 (variable, depends on opponent)
- 2v6 matchups: 1-12 (previously 1-3, now 6-12 with TV478)
- The average depends heavily on matchup distribution and opponent quality.

## Variant Performance Summary
| Variant | Version | Avg Score | Matches | Key Feature |
|---------|---------|-----------|---------|-------------|
| TV478 | v873 | **10.13** | 11 | Always-2-aligners + faster stagnation (BEST) |
| TV477 | v872 | 10.01 | 10 | Always-2-aligners only |
| TV481 | v877 | 8.97 | 13 | TV350 budget + faster stagnation |
| TV350 | v874 | 7.06 | 13 | Baseline (sacred for 5+) |
| TV479 | v875 | ~4.93 | 6 | Instant 4v4 + always-2-aligners |
| TV480 | v876 | ~4.12 | 5 | Reactive 4v4 + always-2-aligners |
