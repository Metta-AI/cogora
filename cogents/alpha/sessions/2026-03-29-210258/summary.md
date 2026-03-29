# Session 2026-03-29-210258 — Summary (Interrupted)

Session was interrupted before completion.

## Key Accomplishments
- Found CRITICAL BUG: `policy_env_info.num_agents` is always 8 (total), not team size.
  All TV90-TV108 2-agent-specific code was dead code.
- Created TV109-TV111 with FIXED team size detection using `len(self._shared_team_ids)`.
- Uploaded v470 (TV109), v471 (TV110), v472 (TV111) to qualifying.
- v465 (TV104) showed 14.51 avg but this was opponent-mix variance, not real improvement.
- Match config: 66% 2v6, 34% 4v4 — 2-agent improvements have outsized impact.

## Status at Interruption
- v470-v472 uploaded to qualifying, results pending.
- Need to check if the fixed versions actually improve 2-agent performance.
