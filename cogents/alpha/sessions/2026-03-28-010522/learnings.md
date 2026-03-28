# Learnings — Session 2026-03-28-010522

## Critical Bug
- `_ALIGNER_PRIORITY = (4, 5, 6, 7, 3)` meant agents 0-3 could never be aligners
- In 4-agent tournament mode, ALL agents were miners → score ~0
- Fix: extend priorities to include all IDs

## Tournament Architecture
- Variable team sizes per match (2v6, 4v4, etc.)
- Policy must handle 2-8 agents gracefully
- Small teams need more conservative budgets (more miners, fewer aligners)

## Non-Determinism
- Same seed + same code → 5.60 to 10.20 (3x variance!)
- Need 10+ episode averages for reliable comparison
- Individual seed comparisons are unreliable for optimization

## Budget Optimization
- More aligners isn't always better: economy must sustain hearts
- 4-agent mode: 1 aligner + 1 scrambler + 2 miners beats 2+1+1
- 8-agent mode: 5 aligners + 1 scrambler + 2 miners is good
- Scrambler is essential (clips ships scramble aggressively)

## What Didn't Work
- Network-distance scoring: caused wipeouts (agents went too far from hub)
- Higher retreat margin: too conservative, wasted alignment time
- 2nd scrambler late game: took away aligner, reduced score
- Old priority ordering for 8 agents: agents 4-7 performed worse than 0-3 as aligners
