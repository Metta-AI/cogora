# Session 2026-03-28-231500 Learnings

## Key Discovery: Economy-Gated Budgets + Chain Expansion
The best local scoring comes from combining two innovations:
1. **Economy-gated aligner budgets**: Scale aligners based on min_res thresholds
   (not fixed counts). Prevents the late-game collapse caused by heart starvation.
2. **Chain expansion weights**: expansion_weight=20 (2x default) strongly prefers
   junctions that unlock other junctions, building connected networks faster.

## Local Scoring Progression (8a, default seed)
| Policy | Score | Key Change |
|--------|-------|------------|
| Aggressive | 2.55 | 6 aligners, 1 miner — economy collapses step 2000 |
| Balanced | 3.16 | Economy-gated budgets, silicon mining — +24% |
| AdaptiveV3 | 3.77 | Dynamic scaling (1-5 aligners) — +48% |
| ChainExpand | 5.91 | expansion_weight=20 + explore idle — +132% |
| ChainDefense | 6.49 | + late-game scramble defense — +155% |

## Tournament vs Local Disconnect
Local scores do NOT predict tournament performance:
- Aggressive: 2.55 local → 6.54 tournament (#1)
- ChainExpand: 5.91 local → 5.52 tournament (#4)  
- ChainDefense: 6.49 local → 3.06 tournament (#14!)

Key reason: tournament opponents are WEAKER than the clips AI used locally.
- Against weak opponents, aggressive play (max aligners, idle-scramble) works best
- Against strong opponents, economy management prevents collapse
- Defense scrambling wastes hearts vs weak opponents (no benefit from denying their score)

## Multi-Seed Variance
Scores vary 2-4x between seeds on the SAME policy:
- AdaptiveV3: 1.84, 5.13, 8.81 (4.8x range)
- ChainExpand: 2.09, 5.99, 5.54 (2.9x range)
- ChainDefense: 5.50, 6.21, 3.00 (2.1x range)

ChainDefense has the lowest variance — defense helps on bad seeds.

## What Didn't Work
- MaxChain (expansion_weight=30): Agents chase distant junctions, ignore nearby easy ones
- AggroChain (Aggressive + chain weights): Chain weights hurt with too many aligners
- Lower economy surplus threshold (50 vs 100): Collapses 8a economy
- Wider exploration offsets (35 vs 22): Delays early game

## expansion_weight Sweet Spot
- Default (10): Adequate but doesn't prioritize chain-building
- 20: Optimal — +132% local improvement
- 30: Too high �� agents walk too far for chain targets

## Silicon is THE Bottleneck
Only 45 silicon extractors on map. Silicon depletes step 3000-3500, killing hearts.
Silicon-priority mining delays collapse but doesn't prevent it.
Fundamental limit: 5000-step games outlast silicon supply.

## Path to Score >10
1. v290 is #1 at 6.54 (heuristic ceiling in tournament)
2. Need tournament opponents to get stronger for economy policies to shine
3. OR need a qualitative improvement (RL, LLM cyborg that works)
4. With 67 matches, v290 is stable — we've likely reached heuristic tournament ceiling
