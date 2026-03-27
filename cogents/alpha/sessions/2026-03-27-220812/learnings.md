# Learnings — Session 2026-03-27-220812

## Key Findings

1. **Gear churn is the #1 economy drain**: Agent role switching forces gear re-purchase (6 resources each). Reducing emergency threshold from 3→1 and keeping budget at 3 (not 2) during emergencies cut gear switches from 8→3 per game and eliminated deaths in best game.

2. **Hub proximity bias works**: Junctions within 15 tiles of hub last ~79 ticks vs ~68 without bias. Ships expand from corners inward, so hub-proximal junctions are the last to be scrambled.

3. **Scramblers are high-value**: A single scrambler disrupts 100+ enemy junctions per game. But 2 scramblers leaves too few miners (2) to sustain the economy.

4. **Heart production is the fundamental bottleneck**: ~335 hearts/game with 3 miners. Each alignment costs 1 heart. Can't brute-force score > 10 without either more hearts or longer-lasting alignments.

5. **Wipeouts are map-dependent**: ~20% of games wipe out regardless of policy (starter policy also wipes out). All agents die at step ~50 when territory doesn't activate on the map.

6. **Hub camping matters**: 20-step hub camp gives territory time to activate and heal agents to 100+ HP. Reducing to 5 steps hurts scores significantly.

## What Worked
- Scrambler at step 400: +0.5 score avg
- Hub proximity penalty (steep > 15 tiles): +0.3 score
- Lower heart batch (2 vs 3): faster cycling, +0.2 score
- Reduced gear churn: +0.5 score from fewer deaths

## What Didn't Work
- 6 aligners (only 2 miners): economy collapse, avg 1.07
- 2 scramblers (only 2 miners): economy collapse
- Lower miner hub distance (15 vs 18): restricted mining too much
- Aggressive miner retreat (hp < dist + 20): miners barely function, avg 0.50
- Lower target switch threshold (1.5 vs 3.0): marginal/no impact

## Next Steps
- Territory-aware pathfinding could reduce deaths and travel time
- Adaptive scrambler activation based on enemy junction count
- Longer game testing (10k+ steps) to see late-game dynamics
- Consider multi-phase strategy: economy → expand → defend
