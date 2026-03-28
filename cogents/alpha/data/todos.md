# Todos

- [ ] Achieve score > 10 in CogsVsClips (heuristic ceiling ~2.8, need trained RL)
- [ ] **GPU-accelerated RL training** — CPU at 10K SPS too slow. LSTM learns but
  can't deploy (inference too slow). Need GPU for faster training AND faster inference.
- [ ] **Curriculum training** — Start on tutorial.aligner/miner, transfer to arena,
  then machina_1. Full game has sparse rewards that prevent learning from scratch.
- [ ] **Shaped rewards** — Add intermediate rewards for resource collection, heart
  acquisition, gear equipping, junction proximity. Current reward is too sparse.
- [ ] **Imitation learning** — Use heuristic policy as teacher, train RL to mimic,
  then fine-tune with RL. Bootstraps learning from heuristic's existing strategy.
- [ ] **Monitor v259 tournament convergence** — Currently at 2.52 (#38, 25m).
  May settle to 2.2-2.5 like other versions.
- [ ] **SmallTeamPolicy validation** — v253 at 2.20 in tournament despite 33% local gain.
  Need 100+ matches to see if it converges higher than vanilla (2.14-2.18).
- [x] Discovered tournament uses 75% 4-agent games (1v3, 2v2, 3v1 splits)
- [x] Created AlphaSmallTeamPolicy — VOR 1.23, 33% better locally
- [x] LSTM RL learns economy but too slow for tournament inference
- [x] Stateless RL can't learn (stuck at max entropy)
- [x] All heuristic versions converge to 2.18-2.52 in tournament
- [x] Hub starts with 5 hearts regardless of team size — free early alignment
