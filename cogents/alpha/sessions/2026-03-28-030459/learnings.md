# Learnings — Session 2026-03-28-030459

## Key Achievement
- **#1 on leaderboard** (v132 = our network-distance targeting) with score 3.51
- Previous best: v65 at #2 with 3.24

## Network-Distance Targeting (BIGGEST WIN)
- Replaced aggressive hub-penalty scoring with network-distance scoring
- Old: penalized junctions far from hub (prevented network expansion)
- New: penalty based on distance to NEAREST hub or friendly junction (enables chaining)
- Expansion weight boosted from 8.0/48 to 10.0/60
- Local 20-seed avg: 4.98 (up from ~4.1 baseline, +20%)
- Best single seed: 14.85

## Non-Determinism is Massive
- Same seed + same code: can give 0.00 or 6.70
- Need 20+ seeds for reliable comparison
- Individual seed comparisons are MEANINGLESS for optimization
- This was the biggest time-waster: debugging "regressions" that were just variance

## Failed Experiments (Don't Repeat)
- Heart batch 3→4: CAUSED WIPEOUTS (economy couldn't sustain)
- Deposit threshold 12→16: inconclusive
- Stable budgets (4A+1S+3M): actually WORSE (other session's 10-seed: 2.81)
- Opportunistic deposit: inconclusive
- 2-hop expansion scoring: inconclusive
- Scrambler only for >=6 agents: didn't help

## Wipeout Analysis
- 10-20% of games score 0.00 (agents die and never recover)
- Some seeds are map-dependent (starter policy also scores 0.00)
- BUT: non-determinism means a "wipeout seed" can sometimes score 6+
- Wipeout prevention could add ~1 point to average (eliminating 10% * 5 avg)

## Tournament Architecture
- v132 at #1 (3.51), v65 at #2 (3.24)
- Matches are alpha.0 versions playing against each other (head-to-head)
- Variable team sizes: 2v6, 4v4, etc.
- Tournament matches take >60 minutes each
- Local 8-cog avg ~5 but tournament avg ~3.5 due to small-team matches

## Score Theory
- Score = avg aligned junctions per tick over entire game
- To get >10 avg: need ~10 junctions aligned for most of the game
- Map has ~65 junctions, hub aligns within 25 tiles, junctions chain at 15
- Economy bottleneck: hearts cost 28 total resources (7 each element)
- 2 miners can produce ~1 heart per 25 steps → 5 aligners consume ~1 heart/10 steps
- Economy can barely keep up with 5 aligners → 4 is safer

## What to Try Next
- Fix wipeout recovery (agents with hp=0 just hold forever)
- Optimize small-team (2-4 agent) performance (tournament weight)
- Study why v65 did well in tournament (may have simpler, more robust logic)
- Try dynamic role count based on observed map layout
