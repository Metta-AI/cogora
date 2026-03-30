# Session Summary — 2026-03-30-180756

**Main finding: Heuristic ceiling confirmed at ~15.05. All parameter tuning yields diminishing or negative returns.**

## Key Results
- v716 (TV350, hotspot=-10) remains #1 at 15.05 with 20 matches
- Created 20+ new variants (TV386-TV411, v775-v797)
- ALL fine-tuning variants performed worse in tournament:
  - v783 (expansion_weight=12): 13.33
  - v785 (hotspot=-11): 13.15
  - v786 (lower retreat): 7.88
  - v790 (expansion_weight=12): 2.18
- Density variants from previous session confirmed as LOCAL-ONLY trap

## LLM Cyborg (v797)
Created TV411: LLM cyborg using TV350 as heuristic base with Anthropic runtime adaptation.
This is the paradigm shift path — LLM can break stagnation patterns that pure heuristics can't.
Results pending.

## Competitive Position
- Top 36 leaderboard positions are ALL our variants (14.46-15.05)
- Best opponent: slanky at 6.71 (rank 374)
- Goal of >10 achieved with massive margin (15.05)

## Critical Learning
Local testing vs Clips AI does NOT predict tournament performance. Always validate in tournament.
