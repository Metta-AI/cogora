# Session 2026-03-29-010815 Learnings

## Critical Discovery: Local vs Tournament Disconnect is HUGE

| Policy | Local 8a | Tournament (avg) |
|--------|----------|------------------|
| Aggressive (v290) | 3.61 | 6.84 |
| UltraV3 (chain expand + Aggressive) | 11.47 | ~1.0 (4v4) |
| Coop (no scramble) | — | ~1.5 (4v4) |
| EconMax (50% miners) | — | ~1.3 (4v4) |

**Chain expansion helps locally but DESTROYS tournament score.** expansion_weight=20 causes
agents to burn resources much faster → earlier economy collapse in tournament.

## Tournament Scoring is Cooperative
Both teams ALWAYS get the SAME score. The scoring formula makes this guaranteed.
This means opponent behavior directly affects OUR score:
- Strong opponent that maintains many junctions → high score for both teams
- Weak/disrupted opponent → low score for both teams

## Scrambling is ESSENTIAL
Removing scrambling (AlphaCoop) → 6a score drops from 2.75 to 1.16.
Scrambling is NOT about denying opponent score — it's about **clearing enemy
junctions that block our network expansion**.

## num_agents Bug
`policy_env_info.num_agents` returns TOTAL agents (8 in 4v4), not per-team (4).
This causes budget overflow: 4+ aligners allocated for a 4-agent team → zero miners.
v290 accidentally works WITH this bug. Created AlphaTeamFix (v327) to test proper
per-team budgets.

## Tournament Environment Changed
v324 (same Aggressive code as v290) scores much lower:
- 6a: 2.75 (was 7.78 for v290) — ALL 10 matches exactly 2.75
- 4a: avg 1.95 (was avg ~6.4)
- 2a: avg 5.85 (similar to v290's ~6.1)

Different opponent versions or game parameters may have changed.

## Multi-Seed Variance (local)
UltraV3 8a across 5 seeds: 11.47, 4.14, 9.81, 6.57, 5.21
Average: 7.44, range 2.8x. Seed/map matters enormously.

## What Didn't Work
- Chain expansion (expansion_weight=20): 3x better locally, 7x WORSE in tournament
- Zero scramblers: essential for network expansion, removing them kills score
- Conservative alignment (50% miners): worse than Aggressive at everything
- Economy surge (mine first, then align): slower start always loses

## What Works
- Aggressive alignment pressure with idle-scramble (v290 approach)
- Fast start (no batching first 200 steps)
- Tight retreat margins (keep agents productive longer)
- Silicon-priority mining delays bottleneck

## Path to >10
1. Fix num_agents bug (TeamFix v327) — proper per-team budgets could help
2. Tournament environment understanding — opponents and format matter hugely
3. The 2a format consistently produces highest scores (5.85 avg, 7.03 max)
4. Need fundamentally different approach or opponent cooperation strategy
