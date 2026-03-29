# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v422=12.83
- [x] v451 = 12.98 (#1, 65 matches) — TV82 baseline, robust local optimum
- [x] Found: all heuristic tweaks (TV112-TV122) score worse than TV82 baseline
- [x] Found: retreat margin=20 is well-calibrated (reducing it hurts)
- [x] Found: scramble behavior is essential for defense (removing it catastrophic)
- [x] Found: 2-agent budget changes all hurt (accidental 8-agent budget is optimal)
- [ ] **Try RL training** — heuristic ceiling at ~13.0 confirmed; GPU needed for breakthrough
- [ ] **Study opponent strategies** — gtlm-reactive is hardest (8.77 avg)
- [ ] **Improve 2v6 performance** — weakest config (11.6 avg, 66% of matches) but all 2v changes hurt so far
- [ ] **Investigate resource economy** — silicon bottleneck visible in logs
- [ ] **Consider entirely different architecture** — e.g., communication between agents, map memory
