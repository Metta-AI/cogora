# Session 2026-03-30-010306 — Summary

## Goal
Improve tournament performance from v495 (TV133) baseline at 12.44 comp avg.

## Key Results
- **v502 (TV138) = 14.19 avg vs v54** (+14% over baseline) — current best
- **v507 (TV143)** uploaded — expected ~14.27 avg (optimal combo)
- Created TV134-TV144 (v496-v508): 13 new tournament variants
- Self-play best: TV139 blitz at 6.40 per cog (8v0)
- Tournament best: TV138 combined (TV136 2a + TV137 4a + TV135 6a)

## Strategy
Systematic budget optimization across team sizes (2a, 4a, 6a):
- 2a: ultra-fast dual align from step 1 (TV136)
- 4a: original TV82 slightly better than faster variants vs strong opponents
- 6a: faster aligner ramp thresholds (TV135)
- Blitz start (TV139) too aggressive for 4a economy
- Economy support (TV140) for 2a fails — dual aligning always better

## Uploaded Versions
v496-v508 (TV134-TV144), all in competition or qualifying

## Status at End
- v507 (TV143) and v508 (TV144) in competition/qualifying — awaiting results
- v505 (TV141) qualifying: 11.17
- v506 (TV142) qualifying: 13.59
