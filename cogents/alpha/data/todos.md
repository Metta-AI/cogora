# Todos

- [ ] Achieve score > 10 in CogsVsClips (current best 7.03, need ~43% improvement)
- [ ] **Monitor v327 (TeamFix) tournament results** — uses actual team size for budgets
- [ ] **Monitor v331 (Focused), v332 (SustainV2) results** — user-created variants
- [ ] **Investigate tournament environment changes** — v324 scores much lower than v290
- [ ] **Study real opponents** — Paz-Bot, slanky, gtlm-reactiv, coglet-v0 appearing
- [ ] **Fix num_agents bug across all policies** — total vs per-team impacts all budgets
- [ ] **GPU-accelerated RL training** — heuristic approach may have reached ceiling
- [ ] **Optimize 2-agent format** — highest scores come from 2a format (avg 5.85, max 7.03)
- [x] CREATED: UltraV3 (11.47 local 8a, ~1.0 tournament — chain expand hurts tournament)
- [x] CONFIRMED: Chain expansion HURTS tournament despite 3x local improvement
- [x] CONFIRMED: Scrambling is ESSENTIAL (removing it → 6x worse score)
- [x] CONFIRMED: Tournament scoring is cooperative (both teams same score)
- [x] DISCOVERED: num_agents is total (8 in 4v4) not per-team (4)
- [x] DISCOVERED: Tournament environment changed — scores much lower across board
