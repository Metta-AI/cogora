# Session Summary: 2026-03-28-160849

## Objectives
- Get to top of leaderboard for CogsVsClips (target: score > 10)

## Key Achievements
1. **Discovered tournament structure**: 75% 4-agent games, 25% 8-agent games
   with asymmetric team splits (1v3, 2v2, 3v1)
2. **Created AlphaSmallTeamPolicy**: Optimized for small teams, 33% better locally,
   VOR 1.23 (4x better than vanilla)
3. **Attempted RL training**: LSTM learns basics but too slow for tournament,
   stateless can't learn at all
4. **Confirmed heuristic ceiling**: All versions converge to ~2.2 in tournament
5. **Uploaded v250-253, v256-257, v263**: Various policy versions for tournament testing

## Scores
- Best local: SmallTeam avg 3.45 at 10k steps (4 agents, 5 seeds)
- Best tournament: v259 at 2.52 (#38, 25 matches) — uploaded by another worker
- Our best: v253 (SmallTeam) at 2.20 (#132, 60 matches)

## Blockers
- Target >10 requires trained RL agents (heuristic ceiling at ~2.8)
- CPU training too slow — need GPU access
- LSTM too slow for tournament inference, stateless can't learn

## Next Steps
1. GPU-accelerated RL training with LSTM architecture
2. Curriculum learning: tutorial → arena → machina_1
3. Shaped rewards for intermediate achievements
4. Imitation learning from heuristic as training bootstrap
