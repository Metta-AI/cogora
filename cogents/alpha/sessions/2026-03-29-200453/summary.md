# Session 2026-03-29-200453 — Summary

## Overview
Created and tested 11 new policy variants (TV90-TV101), uploaded 12 versions (v451-v462).
Focused on improving 2-agent (2v6) performance and removing unnecessary scrambling.

## Key Findings
1. **Scores are game-level** — both teams ALWAYS get the same score. Scramble defense essential.
2. **Zero-scramble fails qualifying** — TV94-TV96 scored ~2.5. Must keep scramble.
3. **Reduced heart batch/early aligner KILLS 2v6** — TV91, TV93 drop from ~11 to ~5.4.
4. **min_res >= 7 for 2-agent is marginal** — v451 converged to 12.83 (vs 12.93 baseline).
5. **Faster stagnation hurts** — TV100 at 11.45. Current 300-step threshold is well-tuned.
6. **3 aligners in 4v4 slightly hurts** — economy can't sustain with 1 miner.
7. **Tournament ceiling ~12.8-13.0** with heuristic approach.

## Final Tournament State
- v451 (TV90): 12.83 (36 matches)
- v449 (TV88): 12.93 (84 matches) — remains the most reliable
- v460 (TV99): 12.40 (30 matches)
- v461 (TV100): 11.45 (27 matches)
- v462 (TV101): still qualifying
