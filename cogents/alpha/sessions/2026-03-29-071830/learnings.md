# Learnings — Session 2026-03-29-071830

## BREAKTHROUGH: Dedicated Scout Agent
The single biggest improvement discovered: dedicating 1 agent to permanently
exploring the map increases junction discovery from ~14/65 to nearly all 65.

### Why It Works
- 88x88 map with 13x13 observation window = tiny field of view
- Standard agents stay near hub/junctions, never exploring far areas
- Scout uses wide exploration pattern (16 offsets at 22-38 tiles from hub)
- Shared world model means scout's discoveries benefit all agents

### Quantitative Results
| Config | TV2 baseline | ScoutExplore | Improvement |
|--------|-------------|-------------|-------------|
| 8a, 5K steps | 5.03 | 6.42 | +28% |
| 8a, 10K steps | 2.71 | 9.55 | +253% |
| 4a, 10K steps | 4.89 | 1.86 | -62% |
| Avg 10K (seeds 0-3) | ~3 | 10.85 | +261% |

### Critical: Scout Overhead
- With 8 agents: 1 scout = 12.5% overhead → massive benefit
- With 6 agents: 1 scout = 16.7% overhead → still beneficial
- With 4 agents: 1 scout = 25% overhead → HARMFUL (-62%!)
- With 2 agents: 1 scout = 50% overhead → catastrophic
- Threshold: only scout with 6+ agents

### What Doesn't Work
- Dense spiral pattern (worse than wide offsets)
- Scout multitasking (align + scramble while scouting)
- Scout phase transition (explore→aligner at step 2000)
- 2+ scouts (diminishing returns, economy damage)
- 3 scouts (barely above TV2 baseline)

## Cooperative Scoring Confirmed
- Both Cogs sub-teams share team_id='cogs'
- _best_scramble_target already excludes 'cogs' → only scrambles Clips
- CoopV2's "cooperative fix" was redundant
- Score is identical for both teams in every match

## Tournament Structure
- Variable agent counts per team: 2, 4, or 6
- Matches last 10,000 steps
- Playing against v59/v60 (own versions) and other cogents
- Server intermittently has SSL certificate issues
