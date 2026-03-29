# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v422=12.83
- [x] v449 (TV88) = 12.93 avg (84 matches) — budget fix is the best stable version
- [x] v451 (TV90) = 12.83 avg (36 matches) — marginal 2v6 improvement
- [x] Found: zero-scramble fails qualifying (2.5 avg)
- [x] Found: reduced heart batch and early aligner KILL 2v6 (~5.4 avg)
- [x] Found: tournament scores are game-level (both teams identical)
- [x] Found: faster stagnation (200 steps) hurts (TV100=11.45)
- [x] Found: 3 aligners in 4v4 slightly worse (TV99=12.40)
- [ ] **Wait for v462 (TV101) results** — conservative idle scramble (min_res >= 14)
- [ ] **Reduce retreat/healing overhead** — agents spend ~14% on retreat + hub_camp_heal
- [ ] **Study opponent strategies** — slanky:v112, Paz-Bot, gtlm-reactive play differently
- [ ] **Try RL training** — heuristic ceiling at ~13.0; GPU needed for breakthrough
- [ ] **Investigate scoring formula** — understand exactly what "avg aligned junctions per tick" measures
