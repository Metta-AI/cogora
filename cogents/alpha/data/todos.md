# Todos

- [x] **Check v909/v910 competition results** — avg 1.33, junction collapse from resource thresholds
- [x] **Fix tournament policy thresholds** — competition resources much scarcer than local
- [x] **Add team-size cap** — prevents economy crashes in tournament
- [x] **Add improved aligner to tournament** — hotspot patrol, expansion, idle-mine
- [ ] **Check v913 competition results** — LLM-based with all improvements, still qualifying
- [ ] **Competition score optimization** — v912 avg 1.93. Target: > 10 (qualifying) or higher competition.
- [ ] **2v6 matchup improvement** — scores 0.25-0.28. Need fundamentally different approach for minority play.
- [ ] **Late-game resource depletion** — silicon/carbon hit 0 at step 5000+ on some maps.
  No heuristic fix found. May need RL or smarter extractor discovery.
- [ ] **RL training** — HIGHEST PRIORITY. Only way to break heuristic ceiling. Need GPU.
- [ ] **Study opponent strategies** — mammet is very strong (0.27 in 2v6, 1.36 in 4v4).
  coglet, modular-lstm, gtlm-reactive also competitive.
- [ ] **Port AlphaCog improvements to AnthropicPilotAgentPolicy** — extractor claims,
  resource bias sticky clearing, etc. Tournament policy still missing some features.
- [ ] **Tournament runs 10000 steps** — always test with --steps=10000 locally.
