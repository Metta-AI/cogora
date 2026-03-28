# Session 2026-03-28-211301 Learnings

## Key Discovery: Idle Aligner Waste
In the baseline AlphaCyborgPolicy, aligners spend 60%+ of the game idle-mining
when frontier=0 (no more junctions within alignment network range). Hub resources
reach 500+ while only 14-15 junctions are aligned out of 65 total.

## AlphaAggressivePolicy Changes (3 key improvements)
1. **No early heart batching (steps 0-200)**: Aligners go align immediately with
   1 heart instead of waiting at hub for 3. Gets first junction aligned ~50 steps
   faster. This is the biggest single improvement.
2. **Idle aligners scramble**: When frontier=0 and economy is healthy (min_res>=14),
   idle aligners scramble opponent junctions instead of mining. Denies opponent score
   and creates new alignment opportunities.
3. **Economy surplus detection**: When min_res >= 100, shift to max pressure (only
   1 miner). Converts wasted mining capacity into alignment/scrambling.

## Results (5000 steps, 3 seeds)
| Policy | 4-agent avg | 8-agent avg |
|--------|------------|------------|
| AlphaAggressive (v7) | **2.37** | **3.97** |
| AlphaCyborg baseline | **1.12** | **3.47** |
| Improvement | +112% | +14% |

4-agent improvement is dramatic (2.1x). 8-agent improvement is modest (1.14x).

## Junction Growth Analysis
- Aggressive: 0→25 junctions by step 1500, then declines to ~7 by step 5000
- Baseline: 0→15 junctions by step 1500, then declines to ~12 by step 5000
- The aggressive policy grows the network faster but also collapses faster (more
  hearts consumed → faster silicon depletion)

## Late-Game Economy Collapse (Silicon Depletion)
- Only 45 silicon extractors on map (vs 50-58 others)
- Silicon depletes by step 3500, killing heart production
- Junction count drops from 25→7 as aligners can't get hearts
- This is the main bottleneck preventing score >5
- Economy warning/survival modes didn't help — once silicon depletes, it's over

## What Didn't Work
- **Economy warning mode** (min_res < 30 after step 2000): Too aggressive for
  4-agent games, pulled back pressure too early
- **Relaxed expansion** (removing hub distance limit): Didn't meaningfully increase
  junction discovery, agents already explore well enough
- **Early scramblers** (step 100): No enemy junctions exist yet at step 100,
  wasting 2 agent slots on exploring for nonexistent targets
- **Delayed scramblers** (step 500): Marginally worse than step 200 (AlphaCog default)

## Seed Variance
- Scores vary 2-3x between seeds (e.g., 1.48 vs 2.98 at 4-agent)
- One seed had all agents die immediately (0.0 score) — likely spawn near wall
- Tournament results will converge with enough matches

## Tournament Uploads
- v287: AlphaAggressive (original, 4-agent scrambler issue)
- v288: AlphaCyborg baseline (control)
- v290: Economy fix variant
- v295: Resource-aware idle-scramble
- v299: Delayed scramblers
- v300: Economy warning (too aggressive)
- v301: Simplified budgets (best version — matches v2 performance with cleaner code)

## Opponent Analysis
- Tournament opponents: slanky:v112, Paz-Bot-9005, alpha.0:v11-v14
- No match results yet (games take 10000 steps)
- Match formats: variable team sizes (2+6, 4+4, 6+2)

## Path to Score >10
1. Heuristic ceiling confirmed at ~4 avg, ~5 peak (single seed)
2. Need to sustain 10+ junctions throughout game → requires solving silicon depletion
3. RL training with GPU remains the most promising path
4. Possible heuristic paths: better junction discovery, smarter resource conservation
