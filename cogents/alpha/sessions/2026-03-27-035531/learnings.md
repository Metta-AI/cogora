# Learnings: 2026-03-27-035531

## Game Mechanics
- **Territory is life**: Hub territory (strength 20, decay 1) heals +100 hp and +100 energy/tick.
  Agents outside territory drain 1 hp/tick and die at hp=0 (~50 ticks from start). All operations
  must stay within ~18 tiles of hub.
- **Energy system**: Move costs 4 energy. Base energy cap is 20. Territory gives +100 energy/tick
  (capped at 20), so agents in territory can move every tick. Outside territory, solar gives 1
  energy/tick = 1 move per 4 ticks.
- **Hub economy**: Starts with 24 of each element, 5 hearts. Hearts cost 7 of each element.
  Initial hearts: 3 (24/7=3). Miners must deposit resources for more hearts.
- **Gear stations**: At fixed offsets from hub: (row,col) = aligner(4,-3), scrambler(4,-1),
  miner(4,1), scout(4,3). These are OUTSIDE the 13x13 obs window from spawn - agents must
  navigate blind.
- **Score**: Average number of aligned junctions per tick. Align early for maximum score.
- **Map**: 88x88, ~3326 walls (43%!), 65 junctions, ~200 extractors.
- **Alignment**: Walk aligner onto neutral junction within range 15 of network (or 25 of hub).
  Costs 1 heart per alignment.
- **Death**: Clears gear and hearts. Agent continues as hp=0 zombie (can still move but useless).

## Development Lessons
- **mettagrid_sdk is required**: The existing semantic_cog.py is far superior to hand-coded
  policies. Porting the SDK (23 files) was essential.
- **Gear station offsets were (x,y) not (row,col)**: semantic_cog uses (col_offset, row_offset).
  Swapping these coordinates was a critical fix.
- **Observation is 13x13**: Very limited view. Agents need systematic exploration to find
  junctions. 43% walls make pathfinding critical.
- **Dead-reckoning works**: Tracking estimated global position by counting successful moves and
  calibrating when hub is visible enables navigation to off-screen targets.
- **Random seeds matter a lot**: Scores vary 0.0-3.35 across seeds. Map layout significantly
  affects performance.

## Policy Architecture
- `MettagridSemanticPolicy` (semantic_cog.py): 1281 lines, uses SharedWorldModel, shared junction
  claims, economic bootstrap logic, aligner priority system. Scores 2-3.35.
- `AlphaPolicy` (alpha_policy.py): ~350 lines, simpler role-based heuristic. Scores ~0.1 avg.
  Good for understanding basics but insufficient for competition.
