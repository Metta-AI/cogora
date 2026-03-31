# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in qualifying — v873 (TV478) avg 10.13
- [x] Fix shared_team_ids in PilotCyborgPolicy — role assignment for team 2
- [x] Team-size budget: REGRESSED (v900 avg ~1). Fixed with team_size-2 miner floor.
- [x] Shared extractor claims — miners claim extractors to avoid clustering.
- [x] v903 competition results checked — avg 1.33 (qualifying was misleading at ~10).
- [x] Mining stall detection — added + made aggressive (20/30/50 step thresholds).
- [ ] **Check v909/v910 competition results** — most promising versions with miner floor + stall fix.
- [ ] **Competition score optimization** — competition avg ~1.33 for v903. Need to improve.
- [ ] **Late-game resource depletion** — silicon/carbon hit 0 at step 5000+ on some maps.
  No heuristic fix found. May need RL or smarter extractor discovery.
- [ ] **RL training** — HIGHEST PRIORITY. Only way to break heuristic ceiling. Need GPU.
- [ ] **Study opponent strategies** — coglet, mammet, modular-lstm, gtlm-reactive.
  coglet: effective scrambler. mammet: strong economy. modular-lstm: RL-trained.
- [ ] **CRITICAL**: Budget uses total num_agents=8 for path selection, BUT caps pressure
  to team_size-2 to ensure miners. Both are needed — don't remove either.
- [ ] **Tournament runs 10000 steps** — always test with --steps=10000 locally.
