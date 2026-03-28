# Learnings: 2026-03-28-191208

## Scoring Mechanics (Confirmed)
- Both players in a match get the SAME score (all agents on same team fighting clips)
- Score per cog = 0.0001 × sum_over_ticks(|cogs_network| - 1)
- For score >10: need avg ~11 aligned junctions maintained over 10k steps
- Match configs: 2v6, 4v4, 6v2 (8 agents total, split between policies)
- 6v2 avg score = 5.38, 4v4 avg = 1.26, 2v6 avg = 1.24

## Clips Behavior (Detailed)
- 4 clips ships on each map
- Each ship scrambles cog junctions every 70 ticks (cogs_to_neutral)
- Each ship converts neutral to clips every 70 ticks (neutral_to_clips)
- Clips spread within radius 15 of their network
- Total clips pressure: ~0.114 scrambles per tick
- Our alignment rate with 4 aligners: ~0.12 per tick (roughly equilibrium)

## Policy Comparison
- AlignMax (more aligners): WORSE overall — economy starvation
- V65 targeting (hub_penalty): keeps agents compact/safe, better in tournament
- Base targeting (no hub_penalty): allows expansion but overextends
- Idle-mine >> idle-explore (confirmed from previous sessions: 8.05 vs 3.54)
- Scramblers use as many hearts as aligners but don't score directly

## Map Seed Variance
- MASSIVE: same policy scores 1.5 to 14.7 depending on seed
- Map layout dominates score variance (not policy differences)
- Local testing unreliable without 20+ seeds

## Heuristic Ceiling
- All heuristic policies converge to 2.0-2.8 in tournament (50+ matches)
- v65 outlier at 3.59 (516 matches) — possibly due to early opponent pool
- New uploads (v280-v298) already converging to same range
- No heuristic improvement tested breaks through 3.0 consistently

## Tournament Architecture
- All agents are on the SAME team (cogs vs clips)
- Different policies control different subsets of agents
- No coordination between different policy instances (no shared state)
- cooperation matters: good policies raise the match score for everyone

## Agent Deaths
- Miners die frequently (up to 7 deaths/game) — major efficiency loss
- Each death: lose gear, waste steps recovering, drain economy
- Tighter retreat margins and hub distance limits reduce deaths

## What Works
- V65 hub_penalty targeting (compact, defensible networks)
- Team-size-aware budgets (2v6/6v2 adaptation)
- Resource bias toward scarce element
- Idle-mine for unused aligners
- Reduced retreat margin (15 vs 20)

## What Doesn't Work
- More aligners (5+) — starves economy
- Heavy early scramblers — wastes hearts
- All-in strategies (Blitz, FlashRush) — economy crashes
- Ignoring clips entirely — they overwhelm
