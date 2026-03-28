# Todos

- [ ] Achieve score > 10 in CogsVsClips (best local: 10.63 on one seed, avg ~4.2)
- [ ] **Check v179/v180/v181 tournament results** — these have the critical role fix
- [ ] **Monitor role assignment fix impact** — should significantly improve tournament scores
- [ ] Analyze tournament match logs to understand PvP dynamics
- [ ] Fix wipe bug (~7% seeds, all agents die immediately)
- [ ] Try adaptive zone assignment based on actual junction positions
- [ ] Test with tournament-realistic conditions (pickup vs starter, 8 agents, 10k steps)
- [ ] Consider LLM-enhanced policy (v178) if heuristic ceiling is ~3.0
- [x] CRITICAL FIX: team-relative role assignment for split teams
- [x] Discovered tournament uses 4-agent AND 8-agent game formats
- [x] Re-alignment boost (hotspot bonus) — +14% over V65True
- [x] Budget stability (tighter thresholds) — +16% over RealignBoost
- [x] Zone-based aligner targeting — achieved 10.63 on best seed
- [x] Confirmed scramblers are critical (removing them hurts consistently)
- [x] Fix hotspot_weight=0 bug in V65Replica inheritance chain
