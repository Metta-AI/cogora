# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v410=12.69 (#1), v414=12.57 (#2), v388=12.38 (#3)
- [ ] **Wait for v410/v414 to reach 99 matches** — confirm they hold above v388's 12.38
- [ ] **Try intermediate scramble thresholds** — min_res >= 10 or min_res >= 5 (TV50 uses 7)
- [ ] **Combine TV50's threshold with TV46's targeting** — TV50 (threshold=7) + TV46 (hub penalty)
- [ ] **Study opponents** — Paz-Bot-9005, slanky:v112, coglet strategies
- [ ] **Improve 2-agent performance** — still a tournament drag
- [x] v406/v407 results checked: v406 (TV46) = 11.97 (#6), v407 (TV25) = 12.36 (#4)
- [x] TV25 vs TV24 gap: scramble-focused stagnation is the key differentiator
- [x] TV48 (70% scramble) = best self-play but only 11.75 in tournament
- [x] TV50 (lower scramble threshold) = simplest change, best tournament (12.69)
- [x] TV53 (TV46 + TV48) = #2 at 12.57 — combining hub penalty + scramble works
- [x] Dedicated scramblers (TV52) always hurt tournament (8.59)
- [x] 100% scramble (TV49) too aggressive (9.05)
- [x] Self-play still anti-correlated with tournament for parameter changes
