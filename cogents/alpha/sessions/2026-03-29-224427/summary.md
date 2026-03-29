# Session 2026-03-29-224427 — Summary

## Overview
Tested TV114-TV122 variants targeting retreat reduction, dynamic stagnation,
faster ramp, and dual aligner for 2-agent teams. All scored below TV82 baseline.

## Key Results
- TV82 (v451) = 12.98 avg (65 matches) — confirmed robust local optimum
- TV117 (dynamic stagnation): 12.04 (49m) — slightly worse
- TV118 (reduced retreat): 10.96 (62m) — worse, retreat calibration matters
- TV119 (faster ramp): 11.57 (61m) — worse
- TV122 (dual aligner 2-agent): 11.16 (2m early) — likely worse

## Versions Created
- TV114-TV116 (v475-v477): inherit TV112/TV113 no-scramble — all bad
- TV117-TV119 (v478-v480): stagnation/retreat/ramp tweaks — all worse
- TV120-TV121 (v481-v482): extreme retreat + combo — likely bad
- TV122 (v483): dual aligner for 2-agent — early data bad

## Conclusion
Heuristic ceiling at ~13.0 is firm. Need RL or fundamentally different architecture.
