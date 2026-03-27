# Todos

- [ ] Achieve score > 10 in CogsVsClips (best avg: 2.93 over 5 games, best single: 3.46)
- [ ] Check competition match results (v89/v91/v93/v95 uploaded this session)
- [ ] Investigate wipeout maps (~20% of games, map-dependent, affects all policies)
- [ ] Try territory-aware pathfinding (cost=4 outside territory in A*)
- [ ] Increase heart production (fundamental bottleneck at ~335 hearts/game)
- [ ] Consider adaptive scrambler count based on enemy junction ownership
- [ ] Try longer-range alignment chains (currently limited by hub proximity bias)
- [x] Add scrambler for network defense (106 enemy scrambles/game)
- [x] Hub proximity bias for aligner targeting (junctions last longer)
- [x] Reduce gear churn (emergency threshold 1, budget 3)
- [x] Lower heart batch initial (2 vs 3), moderate scaling
- [x] Stronger expansion bonus (5.0 vs 3.0) for chain building
- [x] Fix scrambler targeting with friendly_junctions (threat_bonus)
- [x] Economy-responsive pressure budgets
- [x] Set up environment (cogames, auth, venv)
- [x] Upload to tournament (v89-v95)
