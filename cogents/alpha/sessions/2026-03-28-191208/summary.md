# Session Summary: 2026-03-28-191208

## Objectives
- Get to top of leaderboard (target: score > 10)

## Key Achievements
1. **Scoring mechanics confirmed**: Both players get same score (cooperative, not competitive). All agents fight clips together.
2. **Clips behavior analyzed**: 4 ships, 70-tick cycle, radius 15 spread. Clips pressure ≈ our alignment rate.
3. **Created 3 new policy variants**: AlphaAlignMax, AlphaDefenseWall, AlphaBlitz, AlphaOptimal.
4. **Uploaded 15+ policy versions** (v280-v298) for tournament testing.
5. **AlignMax disproved**: More aligners = economy starvation. Economy is the bottleneck.
6. **V65 targeting confirmed superior**: hub_penalty keeps agents safe, produces compact defensible networks.

## Scores
- Best local: 14.72 (seed 44, 10k steps)
- Tournament new versions: 2.0-2.6 (converging to heuristic ceiling)
- v285 (V65TrueReplica): 2.61 early (9 matches)
- v65 still #1 at 3.59 (516 matches)

## Blockers
- Heuristic ceiling at ~2.8 confirmed across all variants
- Target >10 requires fundamentally different approach (RL)
- GPU training needed — CPU too slow
- Massive seed variance makes local testing unreliable

## Next Steps
1. Monitor v291 (AlphaOptimal) and v292 (V65Exact) tournament convergence
2. Focus on reducing agent deaths (tighter retreat, hub distance limits)
3. Explore anti-clips strategies (position junctions far from clips ships)
4. Consider GPU-accelerated RL training for breakthrough
5. Study how clips ship positions affect optimal junction targeting
