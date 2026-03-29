# Todos

- [ ] Achieve score > 10 in CogsVsClips (current best: v348 at 7.46, #1 on leaderboard)
- [ ] **Monitor v351 (TournamentV3) and v352 (TournamentV4) results** — still qualifying
- [ ] **Close 7.46→10 gap** — may need fundamentally different approach
- [ ] **Try LLM cyborg in tournament** — AnthropicCyborgPolicy for runtime strategy adjustment
- [ ] **Study top match logs for v348** — understand what drives high/low scoring matches
- [ ] **GPU-accelerated RL training** — heuristic approach may have reached ceiling
- [ ] **Analyze opponent strategies** — Paz-Bot, slanky, coglet-v0, swoopy-v0
- [x] BREAKTHROUGH: v348 TournamentV2 = #1 at 7.46 (beats v290's 6.50)
- [x] CONFIRMED: Idle scrambling at min_res>=14 is THE critical differentiator
- [x] CONFIRMED: Conservative budgets (AdaptiveV3) >> Aggressive for tournament
- [x] CONFIRMED: Team-size cap helps on conservative base, hurts on aggressive base
- [x] CONFIRMED: No scrambling = terrible (v350 at 2.18)
- [x] CONFIRMED: Tournament env changed since v290 era (fresh Aggressive = 3.25)
- [x] CONFIRMED: Economy crash in 4v4 when both policies allocate aggressively
