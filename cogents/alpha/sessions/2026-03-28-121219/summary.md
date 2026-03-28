# Session 2026-03-28-121219 Summary

## One-Line Summary
Discovered idle-explore beats idle-mine in PvP (gear churn fix), clips mode testing shows 10.29 peak, tournament policy v228 uploaded.

## Key Results
- **AlphaCyborgPolicy (V4)**: self-play 5k avg 4.73, PvP clips 10k avg 1.49 — overfits to self-play
- **AlphaTournamentPolicy (VT3)**: PvP clips 10k avg 3.97, best seed 10.29 — much better in PvP
- Idle-explore > idle-mine in PvP due to gear churn avoidance
- Hotspot flip bug fixed in AlphaCogAgentPolicy
- Deposit threshold lowered to 12 for faster economy turnover

## Versions Uploaded
- v195-v197: hotspot flip + idle-mine fixes
- v209: V4 final (AlphaCyborgPolicy)
- v210: AlphaTournamentPolicy (idle-mine)
- v228: AlphaTournamentPolicy (idle-explore) — best PvP version

## Key Insights
- Self-play scores don't predict tournament performance at all
- Gear churn (accidental gear swaps) from idle-mine routing through stations
- machina_1.clips mode is best proxy for tournament conditions
- Heuristic ceiling ~2.15 in tournament; >10 likely requires trained RL
