# Session 2026-03-28-231500 Learnings

## Key Discovery: Extractor Exploration Bug
Miners ignore undiscovered resource types. On 2-agent games, oxygen extractors
were never found, leaving oxygen at 4 while other resources reached 300+. Hearts
blocked entirely since they need 7 of EACH element.

Fix: When bottleneck resource < 7 with 10x resource imbalance and no known
extractors for it, force exploration instead of mining wrong resource.
Result: 2a 0.65→1.66 (+155%), 8a 6.62→8.09 (+22%).

## Retreat Margin Optimization
Original AlphaAggressive had 26 retreat actions vs 19 alignment actions per game.
Tighter margins (base 10 vs 15, hearts*3 vs *5, late +5 vs +10) reduced retreats
to 17 and increased alignments to 36 (nearly 2x). No increase in deaths.

## What Didn't Work This Session
1. **AlphaSustainPolicy** (conservation): Hoarded resources → fewer junctions (6-8 vs 10-14)
2. **AlphaExplorerPolicy** (wider exploration): Delayed early alignment → slower start
3. **Bridge scoring** (prefer cluster junctions): Sent agents too far → -37%
4. **Lower surplus threshold** (100→50): Collapsed economy on good seeds (7.95→3.83)
5. **Early 4a scrambler** (step 500): Lost an aligner slot → 3.34 vs 4.29
6. **Silicon-first mining**: Silicon not actually the bottleneck (60 extractors, not 45)

## What Worked
1. **Tighter retreat margins**: +100% alignment actions, biggest single improvement
2. **Extractor exploration fix**: Critical for 2-agent games, helps all configs
3. **4a 3-aligner budget** (min_res>=50, step>=500): Keeps alignment pressure high

## Performance Summary
- 8a avg: 6.08 (seeds 1-5: 7.97, 4.85, 5.55, 2.64, 9.40)
- 4a avg: 3.50 (seeds 1-5: 2.99, 2.46, 4.73, 2.20, 5.10)
- 2a: improved from 0.65 to 1.66
- Best single seed: 9.40 (8a seed 5)
- Estimated tournament avg: ~4.2 (75% 4a + 25% 8a)

## Seed Variance
- 8a range: 2.64-9.40 (3.6x)
- 4a range: 2.20-5.10 (2.3x)
- Seed-based comparison unreliable (nondeterministic even with same seed in different runs)
- Tournament is the only reliable signal

## Game Mechanics Insights
- Map has 68 junctions, 60 silicon extractors (not 45 as previously thought)
- Best scrambler agent cleared 85 enemy junctions in one game
- Junction count peaks at step 500-1000, declines in late game
- Enemy (Clips AI) grows from 0→17 junctions by step 5000

## Path to Score >10
1. Current avg ~4-6, need 2-3x improvement
2. Heuristic ceiling likely ~8-10 on favorable seeds
3. Need to maintain 10+ junctions throughout entire game
4. Key bottleneck: network expansion stalls when frontier=0
5. GPU-accelerated RL training remains the most promising path for >10
