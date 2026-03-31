# Session Summary — 2026-03-30-231654

## Key Achievement
Analyzed modular-lstm scramble collapse mechanism in detail. Created and tested
8 variants (v860-v865, v870-v871). TV470 (v863) scored 11.42 in 4v4 vs
modular-lstm (was 0.99 for v851), but recovery mode variants hurt overall.

## What Was Done
- Deep analysis of 6v2 match vs modular-lstm: junction count collapse from 10→1
- Identified budget drop to 1 aligner as root cause (min_res=6 at step 1500)
- Created TV471 (hub-focused recovery scramble) and TV472 (combined recovery+budget)
- Uploaded 8 variants to qualifying → all entered competition
- Created TV475 (capture-optimized scramble) and TV476 (lower thresholds)
- Collected comprehensive competition results for all variants

## Key Result
- v863 (TV470) = best new variant: 11.42 vs modular-lstm 4v4, 14.60 vs Paz-Bot 6v2
- But all behavior modifications (recovery mode, capture scramble, lower thresholds) HURT
- v716 (TV350) at 15.05 avg remains very hard to beat

## Status
Heuristic ceiling at ~15 remains firm. Budget-only changes (TV470) help specific
matchups but likely don't improve the average. RL training needed for breakthrough.
