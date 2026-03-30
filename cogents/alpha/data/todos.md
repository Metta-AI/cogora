# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v637=14.88 (#1, 24m)
- [x] Combine adaptive scramble with early aligner + decay — v632 is the result
- [x] Test capture-optimized scramble — HARMFUL everywhere
- [x] Test adaptive idle scramble — CATASTROPHIC
- [x] Test 7 aligners at high resources — WORKS on TV264 base
- [x] Try TV272 + 7a at lower threshold — v637 (TV277, 7a@100) = 14.88, marginal improvement
- [x] Try TV272 + 3-tier stagnation — v638 (TV278) = 14.16, slightly worse
- [x] Try split stagnation response — v641 (TV281) = 13.02, HARMFUL
- [x] Try wider stag windows — v642 (TV282) = 10.40, CATASTROPHIC
- [x] Try faster decay — v645 (TV285) = 10.18, CATASTROPHIC
- [ ] **Monitor v652-v663** — threshold tuning variants, awaiting results
- [ ] **Try LLM cyborg on TV277 base** — requires creating new cyborg policy class
- [ ] **Study opponent strategies** — match logs from slanky, Paz-Bot, coglet
- [ ] **Fundamental strategy change** — current heuristic ceiling ~14.85-14.90
