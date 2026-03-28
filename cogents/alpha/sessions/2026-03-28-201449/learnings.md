# Session 2026-03-28-201449 Learnings

## Key Discovery: Miner Sticky Target Bug in AlphaCogAgentPolicy
The miner resource-switching fix was only in AlphaEconFixAgentPolicy, not in
the main AlphaCogAgentPolicy used by AlphaCyborgPolicy. Miners got stuck on
abundant resources while critical ones (like oxygen) hit 0.

**Fix**: Clear sticky target when:
1. Least resource < 7 and miner is mining a different resource
2. Miner is mining the most abundant resource (>80% of max) while
   least resource is < 50% of max (ratio-based rebalancing)
3. Resource bias changed and least resource is < 14

**Self-play impact**: +86% improvement at 4-agent (avg 1.73 vs 0.93, same seeds)
**Tournament impact**: Minimal — tournament scores remain 2.0-2.5

## Shared World Model Experiment (Failed)
Tried sharing a single WorldModel across all agents so miners could find
extractors discovered by any teammate. **Caused pathfinding deadlock**:
- `occupied_cells()` became too large with shared entity data
- A* pathfinding failed (returned None), putting agents in permanent _hold state
- Reverted immediately. v275/v276 are broken.

## Tournament Score Analysis
- v272 (AlphaCyborg + miner fix): Started at 3.80 (3 matches), settled to 2.03 (24 matches)
- v273 (same policy, different upload): 6.09 (1 match) — lucky outlier
- v274 (Hybrid + miner fix): 0.87 (2 matches) — v65 hub_penalty hurts
- All heuristic versions converge to 2.0-2.5 in tournament
- v65's 3.59 (516 matches) is likely inflated from early weak opponents

## Policy Variants Tested
| Policy | 4-agent avg | 8-agent | Tournament |
|--------|------------|---------|------------|
| AlphaCyborg (pre-fix) | 0.93 | 4.68 | ~2.0-2.5 |
| AlphaCyborg (miner fix) | 1.73 | ~3.0 | ~2.0-2.5 |
| AlphaHybrid (v65 targeting) | 1.01 | 2.72 | 0.87 (2 matches) |
| AlphaSoftHub (network_weight=0.5) | — | 2.22 | ~2.1 |

## What Didn't Work
- **Shared WorldModel**: Breaks pathfinding (occupied_cells explosion)
- **v65 hub_penalty targeting**: Too restrictive, hurts self-play and tournament
- **network_weight=0.5**: Also too restrictive for self-play
- **Heuristic tuning in general**: All variants converge to same tournament score

## What We Know Now
1. Self-play scores don't predict tournament scores
2. Heuristic ceiling is structural at ~2.5 in tournament
3. v65's 3.59 is from playing against weak early opponents, not superior strategy
4. The miner fix is technically correct but doesn't move the tournament needle
5. RL with GPU is likely the only path to >10

## Uploads This Session
- v270: AlphaHybrid (v65 targeting + AlphaCog economy) — qualifying pool
- v271: AlphaSoftHub — qualifying pool
- v272: AlphaCyborg control — competition pool, settled at 2.03
- v273: AlphaCyborg with miner fix — 6.09 (1 lucky match)
- v274: AlphaHybrid with miner fix — 0.87 (poor)
- v275/v276: BROKEN (shared world model bug)
- v277: AlphaCyborg with miner fix (reverted shared model)
- v278: AlphaNoScramblePolicy (all alignment, no scramblers)
- v279: Fresh AlphaCyborg with miner fix
