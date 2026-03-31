# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v873 (TV478) avg 10.13
- [x] Aligner floor for 5+ agents + 4v4 floor: TV488/v884 best overall (avg 9.58)
- [x] Combine TV478 + aligner floor (no desperate mode): Done — TV486/v882 → TV488/v884
- [x] Aggressive stagnation: TV489/v885 REGRESSED (avg 5.90). Don't change stagnation timing.
- [x] Faster aligner ramp: TV490/v888 REGRESSED (avg 6.91). Don't ramp faster.
- [x] 4v4 scrambler: TV492/v889 REGRESSED (avg 8.33). Hurts 4v4 (2.72 vs mammet).
- [x] Scorched earth scramble: TV491/v887 REGRESSED (avg 4.63). Bad idea.
- [x] Shared world model (full): TV496/v893 BROKEN — agents cluster at same hub.
- [x] Shared extractor cache: TV496v2/v895 BROKEN — miners cluster at same extractor, score 0.31.
- [ ] **Heuristic ceiling confirmed at ~10** — v884 avg 9.58. ALL budget/stagnation/architecture mods regress.
- [ ] **Shared extractor with target claims** — the extractor sharing idea has merit but needs
  miners to claim specific extractors (like aligners claim junctions) to avoid clustering.
  This is the most promising architectural direction. Need to extend shared_claims to extractors.
- [ ] **Resource imbalance awareness** — v886 (TV490) inconclusive (avg ~8.56, only 3 data points). Worth retesting.
- [ ] **RL training** — HIGHEST PRIORITY. Only way to break heuristic ceiling. Need GPU.
- [ ] **Pre-game LLM** — analyze matchup before game, set high-level strategy.
- [ ] **Study opponent strategies** — coglet, mammet, modular-lstm all beat us in some matchups.
- [ ] **CRITICAL: Qualifying ≠ Competition** — qualifying avg != competition avg.
