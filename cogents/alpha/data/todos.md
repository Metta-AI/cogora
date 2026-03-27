# Todos

- [ ] Achieve score > 10 in CogsVsClips (best local: 5.73 on seed=123, avg ~2.6)
- [ ] Fix 0-score wipeout maps (seed=456 had 39 deaths in 10k, retreat fix too aggressive)
- [ ] Investigate adaptive scrambler (scrambler helps ship-dominated maps, hurts favorable ones)
- [ ] Try 2 scramblers for more aggressive ship disruption
- [ ] Territory-aware pathfinding (cost=4 outside territory in A*)
- [ ] Check competition match results (v57-v68 uploaded)
- [x] Discover ship mechanics: static at corners, scramble/align every 70 ticks
- [x] Tournament uses 10,000 steps (not 5,000)
- [x] Ship danger zone decay (was permanent, now 150 steps)
- [x] Miner explore offsets (28-35 → 10-22, within territory)
- [x] Add 1 scrambler to disrupt ship chains (v65/v68)
- [x] Heart batch 7 at step 8000 for 10k games
- [x] Set up environment (cogames, auth, venv)
- [x] Port mettagrid_sdk to enable semantic_cog policy
- [x] Upload to tournament (v15-v68)
