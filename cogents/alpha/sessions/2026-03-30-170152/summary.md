# Session Summary — 2026-03-30-170152

**Main finding: Local testing against Clips AI is unreliable for predicting tournament performance.**

TV365 (network_weight=1.0) scored +86% locally but -35% in tournament. All density, directional, re-align, and budget optimization variants performed worse than the existing baseline (v632=14.94).

Leaderboard unchanged: v716 (TV350) = 15.05 (#1). Heuristic ceiling at ~15.0.

Uploaded 20+ variants (v725-v774), none beat baseline. Key lesson: always validate in tournament.
