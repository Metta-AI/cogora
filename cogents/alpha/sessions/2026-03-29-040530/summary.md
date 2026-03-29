# Session Summary — 2026-03-29-040530

## Result: #1 on Leaderboard with v348 TournamentV2 at 7.46 (72 matches)

### Key Achievement
Created TournamentV2 policy (v348) that is **#1 on the beta-cvc leaderboard** at 7.46,
beating the previous #1 (v290 at 6.50) by nearly 1 point. Score is stable across 72 matches.

### Architecture
TournamentV2 = AdaptiveV3 conservative budgets + team-size cap + aggressive idle scramble at min_res>=14

### Tournament Uploads
| Version | Policy | Score | Rank |
|---|---|---|---|
| v348 | TournamentV2 | 7.46 | #1 |
| v349 | AdaptiveV4 | 5.75 | #4 |
| v347 | AdaptiveV3 | 5.54 | #6 |
| v345 | Aggressive | 3.25 | #21 |
| v346 | V3 TournamentOpt | 3.26 | #20 |
| v350 | AdaptiveV5 (no scramble) | 2.18 | #190 |
| v344 | AdaptiveTeam | 2.48 | #94 |

Also uploaded: v351 (TournamentV3), v352 (TournamentV4) — still qualifying.

### Gap to Goal
- Target: >10. Current best: 7.46. Gap: 2.54 points.
- May need fundamentally different approach (RL, LLM pilot) to close remaining gap.
