# Todos

- [ ] Achieve score > 10 in CogsVsClips (heuristic ceiling ~2.8, need trained RL)
- [ ] **GPU-accelerated RL training** — CPU too slow. Need 1000+ epochs for scoring behavior.
- [ ] **Monitor v291/v292/v285 tournament convergence** — AlphaOptimal, V65Exact, V65Replica
- [ ] **Reduce agent deaths** — Miner agent 6 died 7 times in one game. Tighter retreat + hub distance.
- [ ] **Anti-clips positioning** — Prioritize junctions far from clips ships (radius 15 spread)
- [ ] **Fix LLM API access** — AnthropicCyborgPolicy API calls fail locally.
- [ ] **Curriculum training** — Start on tutorial.aligner/miner, transfer to machina_1.
- [ ] **Shaped rewards** — Intermediate rewards for resource collection, hearts, gear, alignment.
- [ ] **Imitation learning** — Use heuristic as teacher, fine-tune with RL.
- [ ] **Late-game silicon depletion** — Only 45 silicon extractors vs 50-58 others.
- [x] CONFIRMED: Both players get same score (cooperative, all agents on same team)
- [x] CONFIRMED: Clips = 4 ships, 70-tick cycle, radius 15 network spread
- [x] CONFIRMED: AlignMax (more aligners) = economy starvation, WORSE than baseline
- [x] CONFIRMED: V65 hub_penalty targeting better in tournament (compact networks)
- [x] CONFIRMED: Heuristic ceiling at ~2.8 across all variants tested
- [x] CONFIRMED: Massive seed variance (1.5-14.7 on same policy) dominates
- [x] CONFIRMED: Scrambler hearts are significant cost (87 hearts for 84 scrambles)
