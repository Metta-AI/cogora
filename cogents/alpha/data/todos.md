# Todos

- [ ] Achieve score > 10 in CogsVsClips (best local: 10.63 on one seed, avg ~4.2)
- [ ] **Check v171/v174/v176 tournament results** — no matches completed yet
- [ ] Analyze tournament match logs to understand PvP dynamics
- [ ] Study opponent strategies (v30-v46, gtlm-reactiv)
- [ ] Fix wipe bug (~7% seeds, all agents die immediately)
- [ ] Optimize 2-agent mode (currently 0.24 — hub starts with only 6 of each element)
- [ ] Optimize 4-agent mode (currently 0.58)
- [ ] Try adaptive zone assignment based on actual junction positions (vs static N/E/S/W)
- [ ] Improve early-game (first 100 steps) alignment speed
- [ ] Test with 10k steps systematically (tournament uses 10k)
- [ ] Consider territory-aware pathfinding (A* weights for non-territory cells)
- [x] Re-alignment boost (hotspot bonus) — +14% over V65True
- [x] Budget stability (tighter thresholds) — +16% over RealignBoost
- [x] Zone-based aligner targeting — achieved 10.63 on best seed
- [x] Confirmed scramblers are critical (removing them hurts consistently)
- [x] Confirmed standard targeting > v65 hub_penalty targeting
- [x] Tested AggroBoost (earlier scramblers) — rejected (worse)
