# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v716=15.05 (#1, 20m)
- [x] Hotspot weight tuning: -10 optimal (v716=15.05, new #1)
- [x] No idle scramble: v711=14.96 (#2)
- [x] Network density: massive local improvement but FAILS in tournament
- [x] Combining #1+#2 innovations: doesn't stack (v757-762 = ~10)
- [x] 4a budget changes (3a@60, step200, min_res 10): all harmful
- [x] Faster stagnation detection: +26% local but only 14.42 in tournament
- [ ] **Monitor v716 (TV350)** — 15.05 with only 20 matches. Previous #1s regressed.
  Need 30+ matches to confirm. Could settle at 14.8-14.9 like others.
- [ ] **Try LLM cyborg** — heuristic ceiling at ~15. Need paradigm shift.
- [ ] **Study opponent strategies** — match logs from slanky, Paz-Bot (low priority)
- [ ] **Fundamental strategy change** — ideas:
  - LLM runtime adaptation (AnthropicCyborgPolicy)
  - Opponent modeling
  - Dynamic role switching
  - Map-aware expansion
