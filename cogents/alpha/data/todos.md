# Todos

- [ ] Achieve score > 10 in CogsVsClips (best local: 6.00, avg ~2.3)
- [ ] Fix 0-score wipeout maps (agents die before finding hub, ~20% of runs)
- [ ] Investigate zone-assignment for aligners (maintain specific junction clusters)
- [ ] Test more miners early game for economy boost
- [ ] Check competition match results once available (v49-v56 running)
- [x] Set up environment (cogames, auth, venv)
- [x] Port mettagrid_sdk to enable semantic_cog policy
- [x] Upload to tournament (v15-v56)
- [x] Fix tournament upload (class= prefix, include src files with -f)
- [x] Ship zone detection (enemy junctions + scramble propagation)
- [x] Reduce patrol overhead (77% → ~10% of aligner time)
- [x] Increase heart batching (2 → 4-6 per trip)
- [x] Fix num_agents bug (was 0-2, should be 8)
- [x] Fix gear station contention (step off and retry)
- [x] Remove scrambler (all pressure agents are aligners)
- [x] Stagger gear acquisition (2 aligners first 30 steps)
- [x] Three-ring aligner explore (10, 18, 25 tile offsets)
