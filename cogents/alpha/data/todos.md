# Todos

- [ ] Achieve score > 10 in CogsVsClips (heuristic ceiling ~2.5-2.8, need trained RL)
- [ ] **GPU-accelerated RL training** — CPU too slow (SPS degrades to 1.2K after 18M steps).
  200 epochs learned mining but not alignment. Need 1000+ epochs for scoring behavior.
- [ ] **Monitor v254/v255/v262/v267-v269 tournament convergence** — multiple versions
  being tested. AlphaCyborg (v255) is best local heuristic.
- [ ] **Fix LLM API access** — AnthropicCyborgPolicy API calls fail locally with retries.
  Works in tournament via secret env. Debug network/auth issue.
- [ ] **Curriculum training** — Start on tutorial.aligner/miner, transfer to arena,
  then machina_1. Full game has sparse rewards that prevent learning from scratch.
- [ ] **Shaped rewards** — Add intermediate rewards for resource collection, heart
  acquisition, gear equipping, junction alignment events. Current reward is too sparse.
- [ ] **Imitation learning** — Use heuristic policy as teacher, train RL to mimic,
  then fine-tune with RL. Bootstraps learning from heuristic's existing strategy.
- [ ] **Late-game silicon depletion** — Only 45 silicon extractors vs 50-58 others.
  Silicon runs out by step 7000, causing economy collapse.
- [x] CONFIRMED: AlphaCyborg > AlphaExpander > SmallTeam > Aggressive (10-seed tests)
- [x] CONFIRMED: Non-determinism exists — ~10-15% wipe rate regardless of policy
- [x] CONFIRMED: CPU RL training impractical (LSTM 200 epochs = 0 alignment score)
- [x] CONFIRMED: 4-agent clips: AlphaCyborg avg 3.24, SmallTeam avg 0.88
- [x] CONFIRMED: 8-agent clips: AlphaCyborg avg 4.34, Expander avg 3.89 (10-seed)
- [x] All heuristic versions converge to 2.0-2.5 in tournament
