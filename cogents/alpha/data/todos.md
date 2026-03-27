# Todos

- [ ] Achieve score > 10 in CogsVsClips (best single: 5.38, best avg: 2.94 over 10 games)
- [ ] Investigate why some games still score < 2 (bad map layouts?)
- [ ] Try territory-aware pathfinding (cost=4 outside territory in A*)
- [ ] Optimize alignment chain building (prioritize junctions that extend network)
- [ ] Reduce aligner travel time (closer target selection, better pathing)
- [ ] Check competition match results (v75-v83 uploaded)
- [ ] Consider late-game strategy shifts (more scramblers when ships dominate)
- [x] Fix economy death spiral: hub camping prevents wipeout (v96/v97)
- [x] Wipeout recovery: agents hold at hub when hp=0 (v98)
- [x] Aggressive pressure budgets: 6 pressure (2 miners) from step 200
- [x] Heart batching: 6/7/8 at steps 500/2000/5000
- [x] Lower retreat margin to 22 (was 28)
- [x] 2nd scrambler at step 1000 (was 1500+)
- [x] Ship danger zone avoidance (100 penalty)
- [x] Discover game is non-deterministic (same seed gives different results)
- [x] Set up environment (cogames 0.21.1, auth, venv)
- [x] Upload to tournament (v15-v83)
