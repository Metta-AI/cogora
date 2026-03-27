# Session 2026-03-27-100443 — Summary

**Status**: Interrupted

Session was interrupted mid-work. Key progress:
- Fixed __init__.py import bug
- Tested shared world model fix (regressed to 0, reverted)
- Baseline confirmed at ~3.32 (5000 steps), 2.78 (full game)
- Tried 6-aligner budget (1.91, reverted)
- Tightened aligner explore offsets, removed 2nd scrambler
- Key insight: shared_junctions dict already handles junction sharing
