# Todos

- [ ] Achieve score > 10 in CogsVsClips (current avg ~4-6, need 2-3x improvement)
- [ ] **Check tournament results for v303-v311** — first real competitive signal this session
- [ ] **GPU-accelerated RL training** — CPU too slow. Heuristic ceiling ~8-10.
- [ ] **Better junction chain expansion** — network stalls when frontier=0. Need smarter bridging.
- [ ] **Optimize 4-agent performance** — 75% of tournament. Current avg 3.50.
- [ ] **Study opponent strategies** from match logs when results arrive
- [ ] **Fix LLM API access** — AnthropicCyborgPolicy API calls fail locally
- [x] FIXED: Miners ignoring undiscovered bottleneck extractors (2a oxygen starvation)
- [x] IMPROVED: Tighter retreat margins (+100% alignment actions)
- [x] ADDED: 4a 3-aligner budget (min_res>=50, step>=500)
- [x] CONFIRMED: Conservation/sustain approach counterproductive (resources not the bottleneck)
- [x] CONFIRMED: Wider exploration delays early game (explorer offsets 35 vs 22)
- [x] CONFIRMED: Bridge scoring sends agents too far (-37%)
- [x] CONFIRMED: Early 4a scrambler hurts (loses alignment slot)
- [x] CONFIRMED: Map has 68 junctions, 60 silicon extractors (not 45)
