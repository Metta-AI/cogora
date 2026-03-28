# Session 2026-03-28-181220 Summary

## One-liner
Fixed miner sticky-target resource bug (+164% local), 9.48 peak in 10k self-play, v259 at 2.47 tournament.

## Key Achievements
1. **Root-caused miner resource bug**: Sticky targets lock miners to wrong resources
   even when a critical resource (carbon/silicon) hits 0
2. **Resource-aware miner switching**: Clears sticky target based on critical shortage
   and ratio imbalance
3. **10k self-play peak 9.48**: Nearly achieved target score of >10 in self-play
4. **12 tournament uploads** (v258-v269): Best is v259 at 2.47 (39 matches)
5. **Confirmed team-relative roles essential** for tournament (2+6/4+4/6+2 splits)

## What Didn't Work
- RL training on CPU (0 SPS)
- Global role assignment in tournament
- Hotspot weight in tournament

## State Left
- v258-v269 in tournament, still converging
- v268-v269 have latest fixes (no hotspot, resource switch)
- Tournament ceiling still ~3.59 (v65)
