# Session 2026-03-28-100301 — Interrupted

Session was interrupted before completion.

## Key Work
- Found and fixed CRITICAL station targeting bug: `_acquire_role_gear` used spawn-relative positions as absolute. Agent 1 stuck entire game. Fixed by adding hub offset.
- 5-seed test with fix: avg 3.40 (4.25 excl wipe)
- Tested hub_penalty targeting variant — worse, reverted
- Uploaded v186 (station fix)
- Was testing 5-aligner variant when interrupted

## Key Learning
- Station coordinates must be hub-relative, not spawn-relative
- 12.5% team capacity wasted per game from this bug
