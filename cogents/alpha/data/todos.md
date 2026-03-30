# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v522=15.00 (#1!)
- [x] Discovered: idle scramble ESSENTIAL (-1.2 pts when removed)
- [x] Discovered: self-play does NOT predict tournament performance
- [x] Confirmed: 50% stag scramble optimal
- [x] Discovered: network-aware scramble targeting HARMFUL (-3 to -4 pts)
- [x] Confirmed: heuristic ceiling at ~14.7-15.0
- [x] v541 (faster early ramp) = 13.78, rank #11 — helps 4a, hurts 6a
- [ ] **Fix 6a regression in faster ramp** — only use 3 aligners for <=4 agents, keep 2 for 5+
- [ ] **Study v522 (TV162) vs v525 (TV165)** — lower thresholds (25/40/80) might be optimal
- [ ] **Consider RL training** — heuristic ceiling confirmed; GPU needed for breakthrough
- [ ] **Try LLM cyborg policy** — AnthropicCyborgPolicy might break heuristic ceiling
- [ ] **Analyze opponent strategies** — study match logs for unexploited approaches
