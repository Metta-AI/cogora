# Session Summary — 2026-03-30-212420

## Key Achievement
Created **v840 (TV454)** scoring avg 10.75 in competition — best new variant.
Key innovations: aligner floor of 3 (prevents death spiral) + faster 4a ramp.

## What Was Done
- Analyzed v831/v832 competition results (avg 6-8, much worse than v716=15.05)
- Identified root cause: built on wrong base (TV436 vs TV350)
- Discovered death spiral mechanism: economy dip → 1 aligner → junction collapse
- Created 8 new variants (TV447-TV454, later TV464)
- Found critical bug: aligner floor at step 1 drains initial resources
- Confirmed budget scramblers HURT performance (v851/v852 < v840)
- Uploaded v837-v841, v843, v850 to tournament (12 competition matches analyzed)

## Key Result: v840 (TV454) = avg 10.75
- 6v2: gtlm=12.85, lstm=8.99, mammet=11.47, slanky=15.40
- 4v4: slanky=16.01, Paz=9.63
- 2v6: Paz=11.91/10.28, gtlm=0.18 (outlier)
- Without outlier: avg 12.45

## Status
v840 is best new variant but still below v716 (15.05).
Gap likely from 2v6 matchups where we only control 2 agents.
