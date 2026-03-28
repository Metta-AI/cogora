# Learnings: 2026-03-28-160849

## Tournament Structure
- 75% of tournament games use `cogsguard_4agents` (4 total agents)
- 25% use `cogsguard_machina_1_8agents` (8 total agents)
- Team splits: [0,0,1,1] (2v2), [0,1,1,1] (1v3), [0,0,0,1] (3v1)
- Each team gets its own map instance via multi_team variant
- Hub resources: team.num_agents * 3 of each element, always 5 hearts
- Score is per-team average aligned junctions over time

## SmallTeamPolicy
- Early alignment with free hearts (5 in hub) > mining first for small teams
- Solo agent: always try to align (hearts are "free")
- Fix: when team_summary=None early, assume starting resources (not zero)
- VOR 1.23 vs starter pool (4x better than vanilla 0.32)
- VOR 1.03 over AlphaCyborg
- Local 10k scores: avg 3.45 vs AlphaCyborg 2.59 (33% better)
- Tournament results: 2.20 (same ceiling as all heuristic versions)

## Heuristic Ceiling
- All heuristic versions converge to 2.18-2.52 in tournament with 50+ matches
- Well-converged versions (900+ matches): 2.75-2.88
- v65 outlier at 3.59 (516 matches, possibly different era/opponent pool)
- Local improvements DON'T translate to tournament improvements
- Structural ceiling: ~2.8 for heuristics

## RL Training
- LSTM architecture: learns economy (hearts, mining) but inference too slow for tournament
  - ~14 steps/sec locally vs tournament timeout requirements
  - Entropy collapsed to 0.46 then recovered
  - Junction alignments: stuck at 1-2/episode after 50M steps
- Stateless architecture: can't learn at all (stuck at max entropy 1.609)
  - Feedforward net can't handle sparse rewards without memory
  - No multi-step planning capability
- Both fail to score >10 (or even >2) due to:
  - Sparse rewards (only junction alignment counts)
  - Complex multi-step strategies needed
  - Need shaped rewards or curriculum learning

## Key Insights
1. Game requires complex multi-step reasoning: mine → deposit → get hearts → get gear → find junction → align
2. Trained agents CAN exceed heuristic ceiling (coglet-v0 suggests this)
3. GPU training is essential — CPU at ~10K SPS too slow for meaningful training
4. Curriculum: start with tutorial missions (simpler), transfer to full game
5. Shaped rewards: intermediate rewards for resource collection, heart acquisition, gear equipping
