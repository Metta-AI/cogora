# Session 2026-03-29-030152 Learnings

## Critical Discovery: max_steps = 10000
Tournament games run 10000 steps, not 5000. Previous 5000-step tests underestimated
economy collapse in the second half. Score = avg(net_junction_count) per tick / max_steps.

## Critical Discovery: Economy Collapse in 4a
With Aggressive policy in 4a (2v2), the num_agents bug causes 0 miners → economy collapses
by step 3000-5000. Average junctions drop from 7.74 (first half) to 0.25 (second half).
This halves the tournament score.

| Format | Steps 0-5000 avg | Steps 5000-10000 avg | Total Score |
|---|---|---|---|
| Agg 4a | 7.74 | 0.25 | 2.06 |
| Sustain 4a | ~7 | ~3 | 8.63 |
| AdaptiveTeam 4a | ~11 | ~9 | 8.67 |

## Key Fix: Budget Cap by Team Size
Capping alignment+scrambler budget to (team_size - 1) guarantees at least 1 miner.
This prevents economy collapse while maintaining aggressive alignment pressure.

In tournament, shared_team_ids contains ONLY the team's agents (not opponents),
so team_size is correct. In self-play, it contains ALL agents (both teams), so
the cap is weaker than in tournament.

## Scoring Formula (Exact)
```python
reward = (num_tagged(f"net:{team_name}") - 1.0) * (1.0 / max_steps) per tick
```
- Score = avg junctions in connected network per tick
- "net:" tag = junctions connected to hub via ClosureQuery (max 15/25 unit hops)
- -1.0 excludes the hub
- NOT cooperative: each team scored on their own network

## Previous "Cooperative Scoring" Finding Was Wrong
Both teams get the SAME score in self-play because symmetric policy → symmetric junctions.
In tournament with different opponents, scores differ.

## What Worked
1. Budget cap by team_size (8.67 in 4a 10k, up from 2.06)
2. Higher scramble threshold (min_res >= 20, saves hearts for alignment)
3. Idle-mine when economy weak (sustains resource production)
4. Aggressive base with bug (maximizes alignment pressure when cap doesn't restrict)

## What Didn't Work
1. Silicon-priority mining: over-corrected, caused oxygen/germanium bottleneck
2. No scrambling (SustainV3): 2.77 vs 8.67 — scrambling essential for expansion
3. Max alignment (MaxAlignV2): 1.45 — no economy = terrible
4. Explicit class method delegation: caused noop bug in AdaptiveTeam v1

## Multi-Seed Variance (4a 10k)
Seeds 1-4: 8.67, 3.22, 1.57, 8.72 — avg 5.55, range 4.7x
Map layout (junction distribution) causes massive variance. Nothing we can do.

## Path to >10
1. Best local 4a: 8.72 (seed 4), avg 5.55 across seeds
2. Best local 8a: 19.18 (old cap), 9.24 (universal cap)
3. Tournament mixes formats — weighted avg needs to exceed 10
4. Further gains possible from: faster early alignment, better junction targeting,
   network connectivity optimization, mining efficiency
