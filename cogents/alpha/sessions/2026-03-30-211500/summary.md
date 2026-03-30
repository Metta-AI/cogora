# Session Summary — 2026-03-30-211500

## Key Achievement
Discovered and fixed the **aligner floor death spiral** — the single biggest improvement since v716.

When resources drop low, the budget system was reducing aligners to 1, causing a death spiral:
fewer aligners → lose junctions → economy stress → stay at 1 aligner forever.

**TV446 (v832)** fixes this by maintaining 3 aligners minimum for 6+ agents. Results:
- 7x improvement vs modular-lstm (0.71 → 5.31 avg)
- Scored 16.54 vs Paz-Bot (beats v716's 15.05 record)

## What Was Done
- Analyzed 20+ completed competition matches from previous session
- Identified death spiral pattern via detailed match log analysis
- Created 7 new variants (TV440-TV446) exploring:
  - Proactive scramble when no frontier
  - Scramble claim coordination
  - Mine-when-idle stagnation
  - Aligner floor (2 and 3 minimum)
- Uploaded all to tournament (v826-v832)
- Got early competition results: v832 is promising

## Variants Uploaded
v826=TV440, v827=TV441, v828=TV442, v829=TV443
v830=TV444, v831=TV445, v832=TV446 (best)
