# Learnings — 2026-03-30-051758

## Network-Aware Scramble Targeting is HARMFUL (-3 to -4 pts)

The biggest finding: overriding `_best_scramble_target` to add a 20.0 bonus for
enemy junctions within alignment range causes a **massive performance drop**.

| Policy | Network-Aware | Tournament Score | Matches |
|--------|:---:|:---:|:---:|
| v519 (TV160) | No | 14.69 | 6 |
| v541 (TV185) | No + faster ramp | 13.78 | 31 |
| v537 (TV180) | Yes + 75% stag | 11.97 | 27 |
| v535 (TV179) | Yes | 11.41 | 27 |
| v538 (TV182) | Yes + faster ramp | 11.23 | 26 |
| v540 (TV184) | Yes + adaptive mine | 11.49 | 25 |
| v536 (TV181) | Yes + always-scramble | 7.51 | 27 |

**Why network-aware targeting hurts**: The 20.0 alignable_bonus completely
overrides the distance factor. Agents travel farther to reach in-network enemy
junctions instead of scrambling the nearest one. More travel time = fewer
scrambles per game = less junction turnover = lower cooperative score.

**Key lesson**: Distance should ALWAYS be the primary factor in scramble targeting.
Close junctions are better because more scrambles per time unit drives higher score.

## Always-Scramble Idle is TERRIBLE (v536 = 7.51)

Removing the explore/mine cycling from idle behavior and always scrambling
produces the worst results. In cooperative scoring, maintaining economic output
during idle periods is essential. Agents need to mine and deposit to keep the
economy running for hearts.

## Faster Early Expansion: Helps 2a/4a, Hurts 6a

v541 (TV185): TV160 exact idle + 3 aligners at step < 10, 4 at step < 50.

| Agent Count | v519 (TV160) | v541 (TV185) | Delta |
|:---:|:---:|:---:|:---:|
| 2a | 14.95 (4m) | 14.45 (11m) | -0.50 |
| 4a | 13.26 (4m) | 13.94 (11m) | +0.68 |
| 6a | 15.54 (4m) | 12.74 (9m) | -2.80 |
| Overall | 14.58 | 13.78 | -0.80 |

The 6a regression (-2.80) is because 3 aligners at start with 6 agents leaves
only 3 miners. The economy can't support 5+ aligners later.

## Tournament Score Depends ~50% on Opponent Quality

Both teams ALWAYS get the same score. The highest scoring match this session
was v51(4a) vs v532(4a) = 17.71. In that match, the opponent (v51) aligned
20 junctions by step 2000 while our team only had 4.

Playing against strong opponents that aggressively align produces higher scores
for everyone. Playing against v528 (zero scramble) produces 1.26 scores.

## Self-Play Still Misleading

Self-play scores do not predict tournament performance:
- AlphaCyborg baseline: 2.27 self-play
- TV179 (v535): 2.14 self-play → 11.41 tournament
- TV160 baseline: 1.28 self-play → 14.69 tournament

## Heuristic Ceiling at ~14.7-15.0

Top converged versions (6+ matches):
1. v522 = 15.00 (6m)
2. v525 = 14.83 (6m)
3. v519 = 14.69 (6m)

All use the same base: TV142/TV160 with simple idle behavior (50% scramble,
min_res >= 7, distance-based targeting). Differences are in threshold tuning
(lower 6a resource thresholds, faster stagnation detection).

## What to Try Next

1. **Fix the 6a issue in faster ramp**: Only use 3 aligners at start for
   team sizes <= 4. Keep 2 for 5+ agents.
2. **Combine TV165 + TV160**: v525 (TV165) is currently #2. It combines
   lower 6a thresholds with faster stag entry. Could refine this further.
3. **LLM cyborg**: Heuristic ceiling confirmed. Real-time LLM guidance
   could break through by making context-sensitive decisions.
4. **Study why v522 leads**: TV162's lower thresholds (25/40/80) might
   be slightly better than TV160's defaults (30/50/100).
