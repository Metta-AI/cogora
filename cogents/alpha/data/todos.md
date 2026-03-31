# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v716=15.05 (#1, 20m), v840=10.75
- [x] Aligner floor: helps 6v2 (8.99 vs modular-lstm) but hurts average (10.75 vs 15.05)
- [x] Crisis recovery (TV447): marginal benefit
- [x] 2-agent fix (TV465): always (2,0) + relaxed scramble — marginal improvement
- [x] Zero-scrambler not a bug — v716 also has 0 scramblers
- [x] Budget scramblers HURT: v851/v852 < v840. Don't add dedicated scramblers.
- [x] Aggressive stag scramble HURTS: TV466 avg 4.76 (worse than baseline)
- [x] TV350 base is sacred: v847 (TV462, preserving TV350) = 13.59 (closest to v716)
- [x] Lower 5+ thresholds (TV473/v866): avg 8.71, 4v4=10.38, 2v6=6.09. 15.75 peak.
- [x] Combined innovations don't stack (TV474/v869=5.58 < TV473/v866=8.71)
- [ ] **RL training** — HIGHEST PRIORITY. Heuristic ceiling confirmed. Need GPU.
- [ ] **TV473 vs TV350 head-to-head** — v866 avg 8.71 vs v716=15.05. Need same matchup distribution comparison.
- [ ] **Study modular-lstm deeply** — 2 agents outperform our 6. Their policy is fundamentally better.
- [ ] **2-agent optimization** — 2v6 matchups biggest weakness (0.48-12.98 range). slanky beatable.
- [ ] **Pre-game LLM** — analyze matchup before game, set high-level strategy (not per-step)
- [ ] **TV471 hub-recovery analysis** — v863 scored 11.42 vs modular-lstm. Worth deeper study.
- [ ] **CRITICAL: Qualifying ≠ Competition** — never trust qualifying as predictor.
