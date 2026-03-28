# Learnings — Session 2026-03-28-070654

## Re-alignment Boost: Key Discovery
- **Hotspot penalty was backwards**: The shared_hotspots tracking records when OUR junctions
  get scrambled. The default policy PENALIZES re-aligning these junctions (hotspot_weight=8.0,
  positive count). This is wrong — we WANT to re-align quickly.
- **Fix**: Return negative hotspot_count from `_junction_hotspot_count()`, making the penalty
  into a bonus. With hotspot_weight=8.0, a count of -3 gives -24 points (strong priority).
- **Critical bug found**: AlphaV65ReplicaAgentPolicy sets hotspot_weight=0.0. Any class
  inheriting from it has no hotspot effect (penalty OR bonus) unless explicitly re-enabled.
  Must set `self._hotspot_weight = 8.0` in `__init__`.
- **Result**: +17% average score improvement in self-play (3.95 vs 3.38 baseline, 15 seeds).
  Peak: 11.18 on favorable seed (above >10 target!).

## What Worked
- **Re-alignment boost** (hotspot reversal): Consistent improvement across seeds
- **No scrambler for 4-agent teams**: Marginal improvement (1.06 vs 0.95)
- **Team-aware budgets**: Already proven from previous sessions
- **Lower deposit threshold (12)**: Faster economy cycling

## What Didn't Work
- **Expansion weight 15**: Avg 3.72 vs baseline 3.38. Slight improvement but less than
  realign boost. The default 10 is near-optimal.
- **Network weight 0.2**: Avg 4.79 on 6 seeds, but inconsistent. No clear benefit.
- **Retreat margin 10**: TERRIBLE. Avg 1.93 with two 0.00 seeds. Agents die from
  insufficient HP margin. Keep at 15.
- **V65 hub_penalty targeting**: Avg 3.38 (same as baseline). The tiered hub_penalty
  restricts expansion too much, especially when combined with realign boost (avg 2.20!).
- **MaxAlign (6 aligners)**: Avg 1.70. Economy collapses with only 2 miners.
- **Early heart rush** (skip batching < step 200): Inconsistent. Some seeds improve,
  others get worse.

## Self-Play Score Analysis
- 5K self-play baseline: avg 3.38 (20 seeds, 2 zeros = map failures)
- 10K baseline on best seed: 9.65 (close to target!)
- 10K RealignBoost: 7.41 (one run, seed 5)
- Peak score: 11.18 (5K, seed 5, lucky run)

## Non-Determinism Discovery
- Same policy + same seed gives DIFFERENT scores across runs
- Seed 5 with RealignBoost: 6.97, 8.51, 11.18, 6.97, 0.00, 1.24 across different runs
- This makes reliable evaluation extremely difficult
- Need 20+ seeds minimum, and even then results vary by ~20% between test batches
- Some seeds always fail (map/spawn issues): seeds 9, 13 consistently score 0.00

## Tournament Uploads
| Version | Policy | Key Change |
|---------|--------|------------|
| v166 | Old RealignBoost | Hotspot boost (bug: weight=0) |
| v167 | MaxAlign | 6 aligners (terrible) |
| v169 | Fixed RealignBoost | hotspot_weight=8.0 (first working version) |
| v170 | V65 Realign | V65 targeting + realign (worse) |
| v172 | RB + network 0.2 | Variant, neutral |
| v173 | Pure Fixed RB | Same as v169 |
| v175 | Latest RB | No scrambler for 4-agent |

## Architecture Understanding
- Score = average aligned junctions per tick (cumulative)
- 65 junctions on machina_1 map, 88x88 with walls
- Hearts cost 7 of each element, alignment costs 1 heart
- Key constraint: heart production rate limits alignment rate
- 3 miners sufficient for 4-5 aligners' heart needs
- Travel time (hub↔junction) is the main bottleneck
- Non-deterministic game behavior from simulator internals
