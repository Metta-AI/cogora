# Session 2026-03-29-220607 — Summary

## Overview
Discovered critical `num_agents` bug (always 8), tested no-scramble approaches, confirmed
scramble is essential for defense. All TV109-TV116 changes were harmful or neutral.

## Key Results
- **num_agents bug**: All TV90-TV108 2-agent code was dead (never fired)
- **v473 (TV112, no-scramble 2-agent)**: 2vX=5.53, avg=10.70 — failed
- **v474 (TV113, no-scramble all)**: avg=3.10 — catastrophic
- **v470 (TV109, fixed budget)**: 2vX=5.36 — budget fix hurts
- All TV114-116 variants also failed

## Tournament State
- v451 = 13.31 avg (#1, 27 matches) — effectively just TV82
- External opponents all below 10.5
- Heuristic ceiling confirmed at ~13

## Created
- TV102-TV116 (v463-v477) — 15 versions, all worse than or equal to TV82 baseline
