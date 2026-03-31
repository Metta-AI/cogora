# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v873 (TV478) avg 10.13
- [x] 2-agent optimization: TV478 faster stagnation + always-2-aligners = 2v6 scores 8-12 (was 1-3)
- [x] Aligner floor for 5+ agents: TV484/v880 fixes 6v2 budget collapse (avg 12.66 in 6v2)
- [x] Desperate mode: helps some 2v6 (slanky 13.00) but not all. Mining in desperate mode = REGRESSION.
- [ ] **Fix stuck-at-position bug** — agent gets stuck doing desperate_scramble for 2000+ steps. Need better fallback (explore, not mine).
- [ ] **Combine TV484 aligner floor with TV478 base** — v880 uses TV484 (TV483+floor) but TV483's desperate mode may hurt. Try TV478 + aligner floor ONLY, without desperate mode.
- [ ] **RL training** — HIGHEST PRIORITY. Heuristic ceiling confirmed (~15). Need GPU.
- [ ] **Study new opponents** — gtlm-reactive-v3, random-assay-test, swoopy-v0, coglet-v0.
- [ ] **2v6 is structural** — 2 agents can never hold territory vs 6. Optimize early game speed instead.
- [ ] **Improve 4v4 performance** — v880 4v4 avg 8.66, v877 4v4 vs swoopy 13.73. High variance.
- [ ] **Pre-game LLM** — analyze matchup before game, set high-level strategy.
- [ ] **CRITICAL: Qualifying ≠ Competition** — qualifying avg != competition avg.
