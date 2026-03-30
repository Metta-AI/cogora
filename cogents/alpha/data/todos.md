# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v632=15.17 (new #1, 24m)
- [x] Combine adaptive scramble with early aligner + decay — v632 is the result
- [x] Test capture-optimized scramble — HARMFUL everywhere
- [x] Test adaptive idle scramble — CATASTROPHIC
- [x] Test 7 aligners at high resources — WORKS on TV264 base
- [ ] **Monitor v632 (TV272)** — new #1 at 15.17 (24m), needs 40+ for stability
- [ ] **Monitor v636 (TV276)** — TV264+thresholds 18/30/60, 14.52 at 10m
- [ ] **Try TV272 + 7a at lower threshold** — min_res >= 100 instead of 150
- [ ] **Try TV272 + 3-tier stagnation** — differentiate 2a/4a/6a+ thresholds
- [ ] **Try LLM cyborg on TV272 base** — AnthropicCyborgPolicy might break 15 ceiling
- [ ] **Study opponent strategies** — match logs from gtlm-reactive, coglet-v0
