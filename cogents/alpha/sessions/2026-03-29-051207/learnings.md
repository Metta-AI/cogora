# Learnings — Session 2026-03-29-051207

## Critical Discovery: Cooperative Scoring
- Tournament scoring is COOPERATIVE — both Cogs teams share the same score
- Scrambling opponent Cogs junctions is wasteful (reduces shared score temporarily)
- Scrambling Clips junctions is beneficial (converts non-Cogs to Cogs = +1)
- In self-play, CoopV2 yields +14% total Cogs junctions (16 vs 14) vs TV2

## Architecture Analysis
- 72% of aligner time is idle-scrambling when frontier=0
- Only 7% is actual junction alignment
- Junction discovery limited to ~14 of ~65 per team (13x13 obs radius)
- Exploration radius of ~22 insufficient for 88x88 map

## Map Variance
- Self-play scores across seeds: 1.28-4.33 (TV2, 4a, 5000 steps)
- Map geometry is the dominant factor in scoring
- Good maps: many junctions near hub → fast alignment
- Bad maps: few junctions near hub → low score regardless of strategy

## Heuristic Ceiling
- All top 3 tournament policies converge to ~7.5 (81 matches each)
- TV2 (v348, 7.57), TV3 (v351, 7.49), TV4 (v352, 7.50)
- 7 different policy variants tested, all worse than or equal to TV2 in self-play
- Deviating from TV2's balance in ANY direction hurts performance

## What Doesn't Work
- Wide exploration (ExplorerV2): 0.99 vs TV2's 3.85 (-74%)
- Faster heart cycle (CapturePlus): 2.12 (-45%)
- Faster 4a ramp (TV5): 3.26 (-15%)
- Passive defense (Patrol): 3.58 (-7%)
- Zero miners (MaxPressure4a): 1.44 (-63%)
- Bad map exploration (AdaptiveMap seed 2): 0.83 (-35%)

## What Works (Equal)
- Capture-optimized scramble targeting: matches TV2 in self-play
- AdaptiveMap on good maps: +4% improvement (4.51 vs 4.33)

## Key Strategic Insight
The primary bottleneck is NOT strategy/targeting — it's MAP GEOMETRY and
GAME MECHANICS. On favorable maps, the policy scores 8-9. On unfavorable
maps, 1-3. To break past 7.5 average, need either:
1. Fundamentally better junction chain-building (RL training)
2. Cooperative scoring optimization (only scramble Clips, not Cogs)
3. Map-adaptive behavior that works on ALL map types
