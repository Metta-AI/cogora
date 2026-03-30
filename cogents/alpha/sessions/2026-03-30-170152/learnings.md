# Learnings — Session 2026-03-30-170152

## Key Finding: Local Testing is Unreliable

**Local testing against Clips AI does NOT predict tournament performance.**

- TV365 (network_weight=1.0): **+86% local** but **-35% tournament** (9.76 vs 14.94)
- All density variants scored 7-13 in tournament, well below baseline 14.94
- The density approach makes agents too conservative — they cluster near hub and don't expand enough

This is the most important finding of this session. Future sessions should upload directly to tournament for validation, not rely on local testing.

## What We Tried

### 1. Network Density (TV361-TV370) — FAILED in tournament
- network_weight=1.0 (2x default): 8.78 local (+86%), 9.76 tournament (-35%)
- network_weight=2.0: 4.97 local, 9.67 tournament
- network_weight=0.75: 8.16 local, 9.27 tournament
- All worse than baseline in tournament

### 2. Directional Spreading (TV362) — Modest
- Each aligner assigned a direction to prevent clustering
- 6.49 local (+37%), 12.93 tournament (-13.5%)
- Best of the new approach variants, but still below baseline

### 3. Re-align Specialist (TV363) — FAILED
- Agent 0 prioritizes re-aligning scrambled junctions
- 6.69 local, 11.20 tournament

### 4. Budget Optimization (TV396-TV400) — FAILED
- Lowering 4-agent thresholds for more aligners: WORSE
- v770 (always 2 aligners in 4a): 12.91 (best of group)
- v772 (5+ lower thresholds): 10.71
- Economy can't sustain more aligners in small teams

### 5. Combined Approaches — FAILED
- hotspot=-8.0 + density: 4.65 local — actively harmful combination
- 7a@120 + density: 5.39 local — also bad

## Why Density Failed in Tournament

Match log analysis of a v737 4v4 game revealed:
- Only 1 aligner (economy too weak for 2)
- friendly_j=1-2 throughout the game
- Agent stuck cycling: explore → align → scrambled → rebuild hearts
- Dense targeting makes the single aligner too conservative

The fundamental issue: in tournament 4v4 (and 2v6), economy is tight. Density forces agents to stay near hub, but they need to EXPAND to find and align junctions.

## Tournament State

- **#1: v716 (TV350, hotspot=-10, 7a@120) = 15.05 (20m)**
- #2: v711 (TV349) = 14.96 (20m)
- #3: v632 (TV272) = 14.94 (33m)
- Heuristic ceiling remains at ~15.0
- Best non-alpha: slanky at 6.69 (rank 370). We dominate #1-#369.

## What to Try Next

1. **Study match logs from v716 wins** — understand exactly what makes #1 variant win
2. **Opponent analysis** — study slanky, coglet-v0 strategies from match logs
3. **Asymmetric team strategies** — different behavior for 2v6 vs 4v4 vs 6v2
4. **LLM cyborg** — the paradigm shift; let LLM adjust strategy at runtime
5. **Always upload to tournament** — local testing is misleading, tournament is ground truth
