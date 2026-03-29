# Todos

- [ ] Achieve score > 10 in CogsVsClips (current #1 at 6.54, need >50% improvement)
- [ ] **Monitor v313-v316 tournament results** — fresh builds with all fixes
- [ ] **GPU-accelerated RL training** — heuristic tournament ceiling ~6.5
- [ ] **Fix LLM API access** — AnthropicCyborgPolicy could help with adaptive strategy
- [ ] **Study opponent strategies** when stronger opponents appear (currently weak field)
- [ ] **Optimize 4-agent specifically** — 75% of tournament, our weakest format
- [x] CREATED: AlphaChainExpandPolicy (+132% local 8a, #4 tournament at 5.52)
- [x] CREATED: AlphaAdaptiveV3Policy (dynamic economy scaling, #3 tournament at 5.56)
- [x] CREATED: AlphaChainDefensePolicy (defense HURTS tournament, 3.06)
- [x] CONFIRMED: expansion_weight=20/cap=120 is optimal sweet spot
- [x] CONFIRMED: Defense scrambling hurts vs weak tournament opponents
- [x] CONFIRMED: Aggressive approach wins tournament (opponents are weak)
- [x] CONFIRMED: Economy-gated budgets + chain weights synergize locally
- [x] FIXED: Miners ignoring undiscovered bottleneck extractors
