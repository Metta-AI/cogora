# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v873 (TV478) avg 10.13
- [x] Aligner floor for 5+ agents + 4v4 floor: TV488/v884 best overall (avg 9.58)
- [x] Combine TV478 + aligner floor (no desperate mode): Done — TV486/v882 → TV488/v884
- [x] Aggressive stagnation: TV489/v885 REGRESSED (avg 5.90). Don't change stagnation timing.
- [x] Faster aligner ramp: TV490/v888 REGRESSED (avg 6.91). Don't ramp faster.
- [ ] **Heuristic ceiling confirmed at ~10** — v884 avg 9.58. All budget/stagnation mods regress.
- [ ] **RL training** — HIGHEST PRIORITY. Only way to break heuristic ceiling. Need GPU.
- [ ] **Resource imbalance awareness** — v886 (TV490) inconclusive (avg ~8.56, only 3 data points). Worth retesting.
- [ ] **Pre-game LLM** — analyze matchup before game, set high-level strategy. May help adapt to opponent.
- [ ] **Study opponent strategies** — coglet, mammet, modular-lstm all beat us in some matchups.
- [ ] **2v6 is structural** — 2 agents can never hold territory vs 6. Silicon bottleneck on some maps.
- [ ] **6v2 germanium collapse** — in some 6v2 matches (vs coglet, score 2.03), germanium hits 0 causing death spiral.
- [ ] **CRITICAL: Qualifying ≠ Competition** — qualifying avg != competition avg.
