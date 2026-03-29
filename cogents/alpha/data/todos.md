# Todos

- [ ] Achieve score > 10 in CogsVsClips (best local avg 8.13, need ~23% improvement)
- [ ] **Monitor v338 (AllCarbon) tournament results** — best policy, 100% carbon bias
- [ ] **Monitor v328 (CarbonBoost), v329 (Aggressive) tournament results** for comparison
- [ ] **Investigate tournament environment changes** — v324 scores much lower than v290
- [ ] **Study real opponents** — Paz-Bot, slanky, gtlm-reactiv, coglet-v0 appearing
- [ ] **Extend alignment sustainability** — aligners only productive 0-3000 steps out of 10k
- [ ] **GPU-accelerated RL training** — heuristic approach may have reached ceiling
- [ ] **Improve 8a bad-seed robustness** — AllCarbon scores 7.20-9.35 range, reduce variance
- [x] CREATED: AlphaAllCarbonPolicy — avg 8.13 on 8a (4v4), best variant
- [x] CONFIRMED: num_agents "bug" is actually BENEFICIAL for 4v4 (more aligners = better)
- [x] CONFIRMED: Carbon is 3x bottleneck — 100% bias is better than 50%
- [x] CONFIRMED: Scramblers essential (Coop/HighEff without them → 0-1.38)
- [x] CONFIRMED: Mining deposit threshold 12 is optimal (8 and 20 both worse)
- [x] CONFIRMED: -c 8 = 4v4 (main tournament), -c 4 = 2v2 (minority)
