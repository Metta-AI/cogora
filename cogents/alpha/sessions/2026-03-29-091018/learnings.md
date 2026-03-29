# Learnings — Session 2026-03-29-091018

## Critical Tournament Insights

### 1. Don't Change Aligner Budgets for Tournament
Reducing aligner count to preserve economy is ALWAYS worse.
- v370 (TV14, silicon priority): 8.15 vs v368 (TV12): 8.69
- v371 (tournament economy cap): 6.71 — terrible!
- v372 (economy fix): 6.59 — even worse!
TV12's budget scaling from AdaptiveV3 is near-optimal. Don't touch it.

### 2. Chain Push is Neutral-to-Harmful
TV11 chain push (exploring beyond aligned frontier junctions):
- Helps on favorable maps (seed 1: +3.62)
- Hurts on unfavorable maps (seed 2: -1.88)
- Net effect: zero improvement on average

### 3. Stagnation Detection is the Best Single Innovation
TV12's stagnation detection (wider explore after 300 steps of no junction growth)
is worth +0.12 tournament points over TV9 (8.69 vs 8.57).

### 4. Self-Play ≠ Tournament
Self-play 10K averages: TV9=12.32, TV12=12.87, TV13=12.70
Tournament averages: TV9=8.57, TV12=8.69
Gap: ~32%. Caused by playing with weak partners (old versions at 3-5 avg).

### 5. Tournament Environment Details
- `num_agents=8` in tournament (each player controls 4)
- `_shared_team_ids` has only our 4 agents
- Budget scaling uses `num_agents=8` but team cap limits to `team_size-1`
- Silicon depletes to 5 by step 1500 in some matches — but fixing this hurts more

### 6. Burst Explorer Works But Doesn't Help
Agent 7 as dedicated explorer for 400 steps: visited 17/20 map waypoints.
But losing 1 miner for 400 steps costs more than the discovery benefit.

## Score Data
| Policy | Self-Play 10K | Tournament | Notes |
|--------|--------------|------------|-------|
| TV9 (v367) | 12.32 | 8.57 | Proven baseline |
| TV12 (v368) | 12.87 | **8.69** | #1 — stagnation detection |
| TV14 (v370) | 12.70 | 8.15 | Silicon priority hurt |
| TV16 (v372) | ~10 | 6.59 | Budget caps killed it |

## What to Try Next
1. **Combine TV12 + TV15 (parallel session's idle exploration)** — idle step counter approach
2. **Improve targeting** — better junction selection for alignment
3. **Faster initial alignment** — start aligning earlier in game
4. **Better 2-agent behavior** — improve contribution when we have only 2 agents
5. **Study top match replays** — analyze specific v368 matches to understand patterns
