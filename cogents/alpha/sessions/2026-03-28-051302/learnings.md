# Learnings — Session 2026-03-28-051302

## Tournament Architecture Discovery
- Competition pool uses **variable team sizes**: 2+6, 6+2, 4+4 agents
- Base policy assumes 8 agents → breaks at 4 agents (0.55 score vs 2.71 with team-aware)
- Score is "participation-weighted average" — larger teams count more

## Targeting Changes Analysis (v134-v137 era changes)
- `network_penalty` (v134): hurts 10-seed local avg — 3.89 → 5.03 when removed
- `hotspot_penalty` (v137): no benefit, adds complexity
- `expansion_weight` change (5→10): actually HELPS, keep at 10
- `retreat_margin` change (15→20): mixed effects
- `deposit_threshold` change (12→16): hurts locally but helps tournament (v155 at 2.19)

## V65 Score Mystery Resolved
- v65's 3.24 score is inflated from playing against weaker early opponents (v1-v50)
- Current competitive pool is much stronger
- Best recent versions score 2.0-2.6 against current pool
- Replicating v65's code doesn't help — the opponent pool matters more

## Key Tournament Results
| Version | Strategy | Score | Matches |
|---------|----------|-------|---------|
| v65 | Historical base | 3.24 | 321 |
| v155 | V65r + deposit12 | 2.19 | 25 |
| v150 | V65 replica | 1.95 | 27 |
| v148 | 3 scramblers | 1.35 | 42 |
| v149 | 0 scramblers | 1.91 | 43 |
| v145 | Base + bias | 1.99 | 45 |

## What Works
- Base aggressive budgets (4 aligners + 1 scrambler from step 30) are optimal for 8 agents
- Higher expansion bonus (10.0, cap 60) helps local scores significantly
- Lower deposit threshold (12) may help in tournament (faster economy cycling)
- Team-size-aware budgets dramatically help 4-agent configurations

## What Doesn't Work
- Custom budget overrides (conservative, scramble-heavy, no-scramble): all worse
- Resource bias: inconsistent, causes wipeouts on some seeds
- Network-distance penalty: hurts more than helps
- Hotspot avoidance: adds no value
- Economy-first (mine first, align later): terrible — loses too many early ticks

## Next Session TODOs
- Monitor v160/v161 (team-aware) tournament results
- If team-aware works, iterate on 2-agent and 4-agent specific strategies
- Consider opponent-specific counter-strategies
- Test with tournament-specific map configurations
- Investigate what the v60-v75 era code looked like (not in git history)
