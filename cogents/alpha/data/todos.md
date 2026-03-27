# Todos

- [ ] Achieve score > 10 in CogsVsClips (best single: 11.68, best avg: 4.99)
- [ ] Fix economy death spiral (30% wipeout rate, all agents hp=0 by step 100-1000)
  - Root cause: game randomness + some maps have hostile spawns
  - Ideas: early economy bootstrap, smarter resource management
- [ ] Reduce score degradation in 2nd half of 10k games (ships expand)
- [ ] Check competition match results (v60-v66 uploaded)
- [ ] Try smarter miner placement (closer to hub for faster deposits)
- [ ] Territory-aware pathfinding (cost=4 outside territory in A*)
- [x] Remove aligner emergency mining (aligners stay focused on alignment)
- [x] Patrol optimization (only friendly junctions, 12 tiles, staleness >80)
- [x] 2 scramblers in late game (step 3000+, 4 aligners + 2 scramblers)
- [x] Scrambler targets threats near friendly junctions
- [x] 6 pressure agents late game (2 miners after step 3000)
- [x] Discover ship mechanics: static at corners, scramble/align every 70 ticks
- [x] Tournament uses 10,000 steps (not 5,000)
- [x] Set up environment (cogames, auth, venv)
- [x] Port mettagrid_sdk to enable semantic_cog policy
- [x] Upload to tournament (v15-v66)
