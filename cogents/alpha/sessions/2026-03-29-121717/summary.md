# Session 2026-03-29-121717 Summary

**Goal**: Maintain >10 tournament score. **ACHIEVED**: v387=10.05, v378=10.02.

## What Happened
Tested 5 stagnation variants (TV23-TV27) trying to improve TV18's stagnation behavior.
ALL were worse at 10K self-play and in tournament. TV18's stagnation is a local optimum.

## Key Results
- 10K self-play: TV18=10.96, TV25=9.38, TV26=7.60, TV27=4.90, TV24=0.00
- Tournament: v387=10.05 (#1), v378=10.02 (#2), both TV18
- Uploaded v388 (TV25), v389 (TV24), v390 (TV26), v391 (TV27) for tournament signal

## Critical Finding
TV18's stagnation (3-ring at r=22/30/35, 300-step trigger) is uniquely effective.
Far exploration discovers distant junction clusters that compound over 10K steps.
Every modification — tighter, wider, faster, slower, more scramble — hurts.
