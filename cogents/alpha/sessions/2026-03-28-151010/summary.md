# Session 2026-03-28-151010 — Summary

## What happened
- Tested 5 new strategy variants (FlashRush, EconDominance, ScrambleDominance, Hybrid, V65TrueReplica)
- Discovered idle-mine >> idle-explore for AlphaCyborg (avg 8.05 vs 3.54 at 10k clips)
- Tested old deps (cogames 0.19) hypothesis — marginal +0.2-0.3 advantage
- Uploaded 19 tournament versions (v231-v249) with various configs
- Confirmed game reproducibility (seed-dependent, ±3 variance)
- Mapped the true tournament ceiling: 2.75-2.81 for well-converged policies

## Best results
- Local: AlphaCyborg 10k clips seed 5 = 15.51 (avg 8.05 across 5 seeds)
- Tournament: v241 (V65TrueReplica + old deps) settling at ~2.35 (#62-72)
- All new uploads converging to 2.1-2.4 range

## Key insight
Score >10 is not achievable in tournament with current game mechanics. The structural
ceiling is ~2.75-2.81 (well-converged versions at 900+ matches). v65's 3.59 is from a
different era. Focus should be on maximizing tournament ranking and understanding why
old versions (v17-v38) converge to 2.75+ while new versions converge to 2.1-2.4.
