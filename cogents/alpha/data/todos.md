# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v422=12.83
- [x] v442 (TV81) = 13.52 avg — bridge scramble + 2-agent
- [x] Created TV82-TV89 (v443-v450) — chain-value targeting, coordinated scramble, budget fix
- [x] Found: coordinated scramble (penalty=30) hurts scores
- [x] Found: 2-agent budget bug (inheriting TV7's min_res>=50 instead of TV70's 14)
- [ ] **Wait for v449 (TV88) / v450 (TV89) competition results** — budget fix variants
- [ ] **Monitor v447 (TV86) / v448 (TV87)** — chain-value expand + light coordination
- [ ] **Compare v443 (TV82) vs v442 (TV81) at 30+ matches** — confirm chain-value targeting benefit
- [ ] **Tune bridge scramble weights** — current bridge_bonus = chain_val * 8.0; may need tuning
- [ ] **Reduce 35% overhead** — agents spend too much time retreating/healing
- [ ] **Improve 6v2 (2-agent) performance** — gtlm 6v2 gives 3.91; need to handle strong opponents
- [ ] **Study opponent strategies** — slanky:v112, Paz-Bot, coglet, gtlm-reactive
- [ ] **Try RL training** — heuristic ceiling may be near; GPU needed
