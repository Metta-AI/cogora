# Learnings — Session 2026-03-28-040422

## Critical Discovery: Local vs Tournament Performance
- Local self-play scores do NOT predict tournament performance
- AlphaCyborgPolicy scores 3.25 avg locally but ~2.0-2.6 in tournament
- Base SemanticPolicy scores 2.68 avg locally but 3.24 in tournament (v65, #1)
- Tournament is alpha-vs-alpha (our versions play each other)
- Optimizing for self-play may actively hurt competitive play

## Role Oscillation Analysis
- Agents 4-5 switched aligner↔miner 15-17 times per game with hysteresis budgets
- Each switch wastes gear (6 resources) and setup time
- Stable budgets fix oscillation: gear changes drop from 17 to 1
- But locally, oscillating budgets score higher (4.38 vs 2.59 on seeds 11-15)
- Theory: oscillation sometimes gives 5 aligners which produces peak scores

## Hotspot Avoidance
- Implemented junction scramble tracking to penalize ship-zone junctions
- Ships auto-scramble within 15 tiles every 70 ticks → junctions near ships are wasted
- Penalty: +8.0 per observed scramble (capped at 3 = +24.0)
- Single-seed result: 4.12 (reasonable but not breakthrough)
- Needs more testing in tournament context

## Scrimmage Issues
- `cogames scrimmage --seed 42` produces ALL wipeout episodes (10/10 = 0.0)
- Some seeds are pathologically bad — careful with seed selection
- Need diverse seeds for reliable comparison

## Wipeout Analysis
- 10-20% of games score 0.00 (total wipeout)
- Agents die before reaching territory healing zone
- HP starts at 50, drains 1/tick, territory heals +100/tick within 10 tiles
- On bad seeds/maps, agents can't reach territory in time
- Wipeouts cost ~3.5 points on average score

## Tournament Architecture
- v65 at #1 (3.24, 321 matches) is the base SemanticCogAgentPolicy
- v60-v75 era dominates top 10 — simpler is better
- All "improvements" since v75 (budget hysteresis, network targeting, hotspots) are net negative in tournament
- v140 best recent version at 2.66 (23 matches)
