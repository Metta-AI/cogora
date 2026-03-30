# Session Summary — 2026-03-30-212418

## What Was Done
- Analyzed v826-v832 competition results (all worse than v716)
- Created TV447-TV465: crisis recovery, aligner floor, 2-agent fix, adaptive aggression
- Uploaded v833-v836, v849, v851-v852 to tournament
- Analyzed match logs deeply (2v6 vs gtlm death spiral, 6v2 vs modular-lstm patterns)
- Studied semantic_cog.py scoring system (alignment network, scramble targeting)

## Key Result
**v716 (TV350) remains #1 at 15.05**. None of 25+ variants beat it.
- Aligner floor helps 6-agent games (8.99 vs modular-lstm vs 2-5 before)
- BUT floor hurts 4v4 and 2-agent games, lowering overall average
- 2-agent economy fix (always 2,0) gives marginal improvement only
- Heuristic ceiling at ~15 is confirmed — RL needed for breakthrough

## Variants Uploaded
v833=TV447, v834=TV448, v835=TV449, v836=TV450, v849=TV460, v851=TV464, v852=TV465
