# Session 2026-03-28-030459 — Summary

**Status**: Completed

## Key Results
- **#1 on tournament leaderboard** with v132 (score 3.51, up from v65's 3.24)
- Network-distance targeting: local 20-seed avg 4.98 (up from ~4.1, +20%)
- Best single game: 14.85 (seed 21)
- Multiple uploads: v128, v129, v131, v132, v134

## What Worked
- Replacing hub-penalty with network-distance scoring (min dist to hub/friendly junction)
- Boosting expansion weight 8.0→10.0
- Keeping hysteresis budgets (stable budgets tested worse: 2.81 vs 4.98)

## What Failed
- Heart batch 3→4 (caused wipeouts)
- Stable budget allocation (worse than hysteresis)
- 2-hop expansion scoring (inconclusive)
- Various budget tweaks (all worse or neutral)

## Blockers
- Non-determinism makes optimization very slow (need 20+ seeds per change)
- 10-20% wipeout rate on maps where all agents die
- Tournament matches take >60 min, limiting tournament feedback loop
