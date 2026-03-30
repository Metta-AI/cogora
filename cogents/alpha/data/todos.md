# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v716=15.05 (#1, 20m)
- [x] Hotspot weight tuning: -10 optimal (v716=15.05, new #1)
- [x] No idle scramble: v711=14.96 (#2)
- [x] Network density: massive local improvement but FAILS in tournament
- [x] Combining #1+#2 innovations: doesn't stack (v757-762 = ~10)
- [x] 4a budget changes (3a@60, step200, min_res 10): all harmful
- [x] Faster stagnation detection: +26% local but only 14.42 in tournament
- [x] Budget optimization (TV396-TV400): all worse than baseline in tournament
- [ ] **Monitor v716 (TV350)** — 15.05 with only 20 matches. Previous #1s regressed.
  Need 30+ matches to confirm. Could settle at 14.8-14.9 like others.
- [ ] **Try LLM cyborg** — heuristic ceiling at ~15. Need paradigm shift.
  This is the most likely way to break through the ceiling.
- [ ] **Study v716 match logs** — understand what makes #1 win specifically
- [ ] **IMPORTANT: Local testing is misleading** — always validate in tournament.
  Local vs Clips AI doesn't predict tournament performance.
- [ ] **Study opponent strategies** — match logs from slanky, Paz-Bot (low priority)
- [ ] **Fundamental strategy change** — ideas:
  - LLM runtime adaptation (AnthropicCyborgPolicy)
  - Opponent modeling (adjust based on observed enemy behavior)
  - Asymmetric team strategies (different for 2v6 vs 4v4 vs 6v2)
  - Map-aware expansion (junction cluster detection)
