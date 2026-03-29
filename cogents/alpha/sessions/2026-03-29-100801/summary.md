# Session 2026-03-29-100801

Created TV19 policy: one-explorer aligner design.

- Agent 0 uses full-map explore waypoints (r15-r38) during idle time
- Other agents use standard r22 offsets (TV9 behavior)
- Gated on team_size >= 5 (4-agent teams use standard behavior)
- Self-play avg 13.49 at 10K steps (seeds: 10.53, 14.94, 14.01, 14.46)
- +7% over TV9 at 5K steps (consistent across seeds)
- Uploaded v379-v381 to tournament
- Tournament results pending (server overloaded)
