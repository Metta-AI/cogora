# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v716=15.05 (#1, 20m), v840=10.75
- [x] Aligner floor: helps 6v2 (8.99 vs modular-lstm) but hurts average (10.75 vs 15.05)
- [x] Crisis recovery (TV447): marginal benefit
- [x] 2-agent fix (TV465): always (2,0) + relaxed scramble — marginal improvement
- [x] Zero-scrambler not a bug — v716 also has 0 scramblers
- [x] Budget scramblers HURT: v851/v852 < v840. Don't add dedicated scramblers.
- [x] Aggressive stag scramble HURTS: TV466 avg 4.76 (worse than baseline)
- [x] TV350 base is sacred: v847 (TV462, preserving TV350) = 13.59 (closest to v716)
- [ ] **RL training** — HIGHEST PRIORITY. Heuristic ceiling at ~15 confirmed across 50+ variants. Need GPU.
- [ ] **Why v716 > v840?** — v716=15.05 vs v840=10.75. Compare same opponents/distributions.
- [ ] **Study modular-lstm deeply** — 2 agents outperform our 6. Their policy is fundamentally better.
- [ ] **2-agent optimization** — 2v6 matchups are the biggest weakness (0.18-11.91 range)
- [ ] **Pre-game LLM** — analyze matchup before game, set high-level strategy (not per-step)
- [ ] **Don't change TV350 for 5+ agents** — it's optimal for current tournament mix
- [ ] **CRITICAL: Qualifying ≠ Competition** — never trust qualifying as predictor.
