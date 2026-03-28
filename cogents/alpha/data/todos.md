# Todos

- [ ] Achieve score > 10 in CogsVsClips (heuristic ceiling ~2.5, need trained RL)
- [ ] **GPU-accelerated RL training** — CPU too slow (SPS degrades to 1.2K after 18M steps).
  200 epochs learned mining but not alignment. Need 1000+ epochs for scoring behavior.
- [ ] **Monitor v273/v277-v279 tournament convergence** — miner fix + no-scramble variant.
- [ ] **Fix shared WorldModel** — per-agent models miss extractors. Need shared exploration
  without breaking A* pathfinding (occupied_cells explosion). Possible fix: share only
  extractor/junction positions, not walls. Or share a separate "exploration map."
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
- [x] FIXED: Miner sticky-target bug in AlphaCogAgentPolicy (+86% self-play, minimal tournament)
- [x] CONFIRMED: Shared WorldModel breaks pathfinding (occupied_cells explosion)
- [x] CONFIRMED: v65 hub_penalty targeting hurts both self-play and tournament
- [x] CONFIRMED: All heuristic versions converge to 2.0-2.5 in tournament
- [x] CONFIRMED: Self-play scores don't predict tournament scores
- [x] CONFIRMED: CPU RL training impractical (LSTM 200 epochs = 0 alignment score)
