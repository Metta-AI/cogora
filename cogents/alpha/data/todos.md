# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v422=12.83
- [x] v451 = 13.31 (#1 on leaderboard, 27 matches) — effectively TV82 baseline
- [x] Found: num_agents bug — all TV90-TV108 2-agent code was dead (num_agents always 8)
- [x] Found: no-scramble HURTS in all configs (2vX drops from 12 to 5.5)
- [x] Found: budget fix (1,0) for 2-agent HURTS (default 8-agent budget accidentally works better)
- [x] Found: tournament is 66% 2v6, 34% 4v4; self-play dominates
- [ ] **Reduce retreat/healing overhead** — agents spend ~14% on retreat + hub_camp_heal
- [ ] **Study opponent strategies** — gtlm-reactive is hardest (8.77 avg), beat us 3.91 in 2v6
- [ ] **Improve 2v6 vs gtlm-reactive** — only matchup where we score <10
- [ ] **Try RL training** — heuristic ceiling at ~13.0; GPU needed for breakthrough
- [ ] **Investigate resource economy** — silicon bottleneck visible in logs, maybe optimize mining priority
- [ ] **Investigate scoring formula** — understand exactly what "avg aligned junctions per tick" measures
