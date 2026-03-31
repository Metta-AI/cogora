# Todos

- [x] **Check v913 competition results** — v913 in competition, matches running
- [x] **Port AlphaCog improvements to AnthropicPilotAgentPolicy** — done in v920 (network_weight, hotspot)
- [x] **Add territory-responsive scramblers** — v914-v919, helps late game
- [x] **Fix mining resource balance** — threshold 7→21 (v917/v922)
- [ ] **Check v919/v921/v922 competition results** — all in competition, 20+ matches running
- [ ] **Competition score optimization** — v915 avg 1.37, v921 avg ~1.4. Target: > 10.
  Current heuristic ceiling vs strong opponents is ~2-3.
- [ ] **2v6 matchup improvement** — scores 0.25-1.17. Fundamentally hard with 2 agents.
- [ ] **Late-game resource depletion** — silicon/carbon hit 0 at step 5000+.
  Threshold 7→21 helps but doesn't solve. May need smarter extractor discovery.
- [ ] **RL training** — HIGHEST PRIORITY. Only way to break heuristic ceiling (~2-3).
  Need GPU. Heuristic tuning produces diminishing returns.
- [ ] **Study what mammet/modular-lstm do differently** — they consistently beat us.
  Likely using trained ML policies. Download and analyze their match logs.
- [ ] **Investigate LLM cyborg effectiveness** — does the LLM add value vs pure heuristic?
  AnthropicCyborgPolicy (LLM) vs AlphaCyborgV2 (heuristic) — compare scores.
- [ ] **Explore AlphaTournament + territory-responsive combination** — v884 base was historically
  best, but team-size-cap removal + territory scramblers might create best hybrid.
