# Todos

- [ ] Achieve score > 10 in CogsVsClips (heuristic ceiling ~3.59, need trained RL)
- [ ] **GPU-accelerated RL training** — CPU gives 0 SPS, completely impractical.
  Need GPU for training. LSTM RL previously learned economy at 10K+ SPS on GPU.
- [ ] **Monitor v267-v269 tournament convergence** — v268 (EconFix no hotspot) and
  v269 (LateGame no hotspot) have latest resource fix + no hotspot weight.
- [ ] **Curriculum training** — Start on tutorial.aligner/miner, transfer to arena,
  then machina_1. Full game has sparse rewards that prevent learning from scratch.
- [ ] **Shaped rewards** — Add intermediate rewards for resource collection, heart
  acquisition, gear equipping, junction proximity. Current reward is too sparse.
- [ ] **Imitation learning** — Use heuristic policy as teacher, train RL to mimic,
  then fine-tune with RL. Bootstraps learning from heuristic's existing strategy.
- [ ] **Improve 2-agent performance** — Currently 0.88/cog at 4-agent games.
  Tournament uses 2+6/4+4/6+2 splits, so 2-agent games matter.
- [ ] **Late-game silicon depletion** — Only 45 silicon extractors vs 50-58 others.
  Silicon runs out by step 7000, causing economy collapse.
- [x] Fixed miner sticky-target resource bug (carbon bottleneck: 0→1025 at step 1000)
- [x] CONFIRMED: Team-relative roles essential for tournament (global: 1.59 vs team: 2.47)
- [x] CONFIRMED: Hotspot weight hurts tournament, disabled in v268-v269
- [x] 10k self-play peak 9.48 (avg 5.49) — near target possible on good maps
- [x] v259 converging at 2.47 (39 matches) — resource fix helps but not breakthrough
- [x] RL on CPU: 0 SPS, impractical (killed immediately)
- [x] All heuristic versions converge to 2.18-2.52 in tournament
