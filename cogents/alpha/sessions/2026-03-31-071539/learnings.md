# Learnings — 2026-03-31-071539

## CRITICAL: Dedicated Miners vs All-Aligner Budget
- AlphaTournamentPolicy (v884, avg 9.58 historically) uses ALL agents as aligners/scramblers with 0 dedicated miners
- AlphaCyborgV2 (v915, avg 1.37) uses team-size cap forcing 2 dedicated miners
- The all-aligner approach outperforms because:
  - More agents aligning = more junctions faster
  - Idle aligners mine when no frontier junctions
  - Starting resources (24 each) sustain early game
- However, v921 (AlphaTournament) scored only 0.75 vs mammet in current competition
  - The historical 9.58 avg was against easier opponents
  - Current pool (mammet v13, modular-lstm v13) is much harder

## Territory-Responsive Scrambler Scaling
- When losing territory (enemy_j > friendly_j + 2), shifting budget toward scramblers helps
- BUT must gate on team size: in 6v2, don't trigger scramblers (we should overwhelm with aligners)
- Fixed: majority teams only trigger on severe loss (enemy > friendly*2 + 5)
- Helped late-game territory retention: 5-8 junctions (vs 0 before)

## Mining Resource Balance Fix (IMPORTANT)
- Miners kept mining abundant resources (carbon=115) while bottleneck (germanium=9) starved
- Root cause: sticky target clearing threshold was 7 (1 heart worth)
- Fix: raised to 21 (~3 hearts) — miners now switch to bottleneck resource earlier
- Also raised mining stall detection and exploration triggers to 21

## 6v2 Regression from Scrambler Shift
- Territory-responsive scramblers hurt 6v2 badly: random-assay 6v2 dropped 4.34→1.14
- In 6v2, opponent's 2 agents grab junctions first while our 6 disperse
- Minor early deficit (enemy=3, friendly=1) triggered scramblers prematurely
- Fixed by only triggering for majority teams on severe loss

## Economy Death Spiral Pattern
- When ANY resource hits 0 → no hearts (need 7 each) → no aligning → lose territory → lose everything
- Carbon and silicon deplete fastest (map-dependent)
- 67% of observations show hearts=0 in losing matches
- Only 12.6% of time spent contesting (vs 34.5% mining + 29.1% retreating)

## AlphaCog Scoring Optimizations
- network_weight=0.0 (vs default 0.5) allows wider expansion
- hotspot_weight=8.0 with inverted count = bonus for re-aligning scrambled junctions
- These were proven in local play but missing from tournament policy

## Competition Score Ceiling
- Against current opponent pool, scores average 1-3 for all approaches tested
- Target of >10 requires fundamental improvements beyond heuristic tuning
- Best scores: v912 5.32 (vs slanky 4v4), v915 2.96 (vs gtlm 6v2)
- Worst: 0.25-0.28 in 2v6 matchups against strong opponents
