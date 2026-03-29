# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v422=12.83 (#1)
- [x] TV61 (80% scramble) is the local optimum at 12.83
- [x] Tested TV66-TV75 (v427-v436) — all worse than TV61
- [x] 85% scramble worse than 80% (sharp dropoff)
- [x] Dedicated scramblers always terrible (5.94)
- [x] Defensive scramble targeting hurts (10.17)
- [x] Faster early alignment hurts (8.44)
- [x] More aligners when healthy hurts (8.12)
- [ ] **Wait for v434/v436 to reach 99m** — confirm they stabilize at ~11.0-11.3
- [ ] **Try RL training** — heuristic ceiling seems reached; need GPU for meaningful training
- [ ] **Study opponent strategies** — slanky:v112=3.92, Paz-Bot=3.87, coglet=2.2
- [ ] **Explore novel strategies beyond parameter tuning**:
  - Network topology analysis (which junctions unlock the most score?)
  - Opponent modeling (adapt strategy based on opponent behavior)
  - Map-specific optimization (learn map layouts)
- [ ] **Improve 2-agent performance** — v431 (TV70) at 12.06 shows promise
