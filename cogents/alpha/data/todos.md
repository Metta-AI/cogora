# Todos

- [ ] Achieve score > 10 in CogsVsClips (heuristic ceiling ~4 avg, need trained RL)
- [ ] **GPU-accelerated RL training** — CPU too slow. Need 1000+ epochs for scoring behavior.
- [ ] **Monitor v287/v295/v299/v301 tournament results** — AlphaAggressive variants vs opponents
- [ ] **Solve silicon depletion** — Only 45 silicon extractors. Economy collapses step 3500+.
  Junction count drops 25→7. Need proactive silicon mining or resource conservation.
- [ ] **Better junction discovery** — Only reaching ~32/65 junctions. Network plateau at 50% coverage.
  Need smarter exploration patterns to find distant junction clusters.
- [ ] **Fix LLM API access** — AnthropicCyborgPolicy API calls fail locally.
- [ ] **Curriculum training** — Start on tutorial.aligner/miner, transfer to machina_1.
- [ ] **Shaped rewards** — Intermediate rewards for resource collection, hearts, gear, alignment.
- [ ] **Imitation learning** — Use heuristic as teacher, fine-tune with RL.
- [x] CREATED: AlphaAggressivePolicy — 4a +112% (2.37 vs 1.12), 8a +14% (3.97 vs 3.47)
- [x] CONFIRMED: Idle-mining wastes 60%+ of aligner time when frontier=0
- [x] CONFIRMED: Early heart batching (3 hearts) delays first alignment by ~50 steps
- [x] CONFIRMED: Hub accumulates 500+ resources while only 14 junctions aligned
- [x] CONFIRMED: Economy warning modes hurt 4-agent (too aggressive pullback)
- [x] CONFIRMED: Heuristic ceiling at ~4 avg, ~5 peak (single seed)
- [x] CONFIRMED: Seed variance 2-3x (1.48 vs 2.98 on same policy, same agent count)
