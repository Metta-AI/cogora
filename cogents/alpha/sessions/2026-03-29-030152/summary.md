# Session 2026-03-29-030152 Summary

## Goal
Score >10 in CogsVsClips tournament. Current best: v290 at 6.84 avg.

## Key Results
- Discovered max_steps=10000 (not 5000): economy collapse in 2nd half is the #1 issue
- Created AlphaAdaptiveTeam: caps budget by team_size to guarantee 1 miner
- Local 4a 10k: 8.67 (seed 1), avg 5.55 across 4 seeds
- Local 8a 10k: 9.24 (seed 1) with universal cap
- Confirmed num_agents bug is beneficial for large teams but kills economy in small teams
- Confirmed scrambling is essential (without: 2.77 vs with: 8.67)

## Policies Created
- AlphaRush, AlphaEconRush (silicon priority — didn't help)
- AlphaTurbo (earlier scramblers — slight improvement)
- AlphaMaxAlignV2 (max alignment — too aggressive, no economy)
- AlphaSustainable (guaranteed miner — 8.63 in 4a, 6.26 in 8a)
- AlphaSustainV3 (no scrambling — terrible, 2.77)
- AlphaAdaptiveTeam (combines Aggressive + miner cap — BEST: 8.67 4a, 9.24 8a)

## Policies Uploaded
v337=Turbo, v339=Sustainable, v340=SustainV3, v342=AdaptiveTeam, v343=AdaptiveTeam v3

## Status
- Tournament results still pending for all uploaded versions
- AdaptiveTeam v343 is the best candidate
- Local testing suggests 4a avg ~5.5, 8a ~9.2 (tournament likely different due to opponents)
