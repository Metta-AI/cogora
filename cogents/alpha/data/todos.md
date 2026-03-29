# Todos

- [ ] Achieve score > 10 in tournament (self-play: 10.85 avg, need tournament confirmation)
- [ ] **Monitor v362 (AdaptiveScout) tournament results** — especially 6-agent matches
- [ ] **Validate v362 in 6-agent tournament matches** — expect 9-17 based on self-play
- [ ] **Optimize 2-agent performance** — AdaptiveScout reverts to TV2 at <6 agents
- [ ] **Improve scout exploration pattern** — current wide offsets work, but maybe even wider?
- [ ] **Study opponent strategies** — gtlm-reactive, coglet-v0 are real competitors
- [ ] **GPU-accelerated RL training** — could push beyond heuristic+scout ceiling
- [x] BREAKTHROUGH: Dedicated scout agent (+28% at 5K, +253% at 10K!)
- [x] ScoutExplore avg 10.85 at 10K steps (self-play, seeds 0-3)
- [x] CONFIRMED: 1 scout optimal, 2+ scouts hurts
- [x] CONFIRMED: Scout only beneficial with 6+ agents (25% overhead at 4a kills economy)
- [x] CONFIRMED: Scout advantage GROWS over time (5K vs 10K)
- [x] CONFIRMED: Cooperative scoring already implemented (team_id='cogs' shared)
- [x] CONFIRMED: Dense spiral worse than wide pattern for scouts
- [x] CONFIRMED: Scout multitasking hurts (should only scout, not align)
