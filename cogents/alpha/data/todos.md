# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v387=10.05 (#1), v378=10.02 (#2)
- [ ] **CHECK v392-v401 tournament results** — hotspot weight variants (TV28-TV37)
  - v392/v397 = TV28 (hotspot=-10) — MAIN BET, +13.8% in self-play
  - v393 = TV31 (-5), v394 = TV32 (0), v395 = TV33 (-3), v396 = TV34 (-7)
  - v398 = TV35 (-10 + bolder expansion), v400 = TV36 (-10 + stronger silicon)
  - v401 = TV37 (-10 + pure explore stagnation)
- [ ] **Push score higher** — if TV28 confirms, stack more improvements
- [ ] **Study opponents** — Paz-Bot-9005, slanky:v112 strategies
- [ ] **Improve 2-agent performance** — significant drag on average
- [x] **Hotspot weight inversion works in self-play** — TV28 (hotspot=-10) avg 8.91 vs TV18's 7.83
- [x] Non-stagnation improvements tested: faster ramp, bolder expansion, pure explore all HURT
- [x] Stagnation scramble IS beneficial — don't remove it (TV37=3.86 vs TV28=8.91)
- [x] ALL stagnation variants worse than TV18 (TV23-TV27 tested)
- [x] TV18 stagnation (3-ring r=22/30/35, 300-step trigger) is a LOCAL OPTIMUM
- [x] Budget changes ALWAYS hurt tournament
- [x] Scores stabilize at 80+ matches; early scores are volatile
