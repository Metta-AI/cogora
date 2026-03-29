# Learnings — Session 2026-03-29-121717

## Tournament vs Local Play
- **Silicon priority**: Hurts in 8-agent self-play but helps massively in 4v4 tournament
  (10.15 vs 8.69 without). Opponents create resource pressure absent in self-play.
- **Early-game hub_camp_heal**: Territory healing works in tournament but not locally.
  Removing it costs ~1.5 points in tournament.
- **Self-play durations matter**: 5K and 10K give DIFFERENT rankings of the same policies.
  TV25 was +24% at 5K but -14% at 10K vs TV18. ALWAYS test at 10K.

## Stagnation Detection — A Local Optimum
TV18's stagnation (TV12) is extremely sensitive to changes. ALL variants tested worse:
- TV22 (faster trigger 200→300): 7.72 tournament (vs 10+ for TV18)
- TV23 (territory loss + close explore): 3.27 at 5K — aggressive scramble crashes economy
- TV24 (tighter radius 15-22): 0.00 at 10K — completely broken
- TV25 (scramble-focused, no far explore): 9.38 at 10K (vs 10.96)
- TV26 (TV15's full-map waypoints): 7.60 at 10K
- TV27 (TV15's idle-step trigger): 4.90 at 10K

**The specific combination of 3-ring offsets at r=22/30/35 with 300-step trigger
is a local optimum. Every modification hurts.** This is the single most important
finding of this session.

## Why TV18's Stagnation Explore Works
From match analysis: agents exploring at r=22-35 discover distant junction clusters
that compound over time (8→21 friendly junctions by step 1000). Tighter exploration
finds fewer clusters, limiting long-term growth. The "wasted HP" from far exploration
is actually an investment in territory expansion.

## Leaderboard Dynamics
- New policy scores are volatile with <30 matches, stabilize by 80+.
- v387 (TV18 reupload) climbed from 8.00 (1 match) → 10.15 (87 matches).
- Both TV18 uploads converged to ~10.05.

## What NOT to Change in TV18
1. Stagnation timing (300 steps, peak ≥ 5, step > 500)
2. Stagnation explore offsets (3 rings at r=22/30/35)
3. Budget allocations (TV7/TV2 defaults)
4. Hub_camp_heal early-game code
5. Idle scramble threshold (min_res ≥ 14)

## Open Questions for Next Session
1. Can non-stagnation aspects be improved? (miner efficiency, target selection)
2. Would more TV18 uploads help spread risk?
3. Can the 2-agent behavior be improved for better teammate support?
4. What do v388-v391 score in tournament? (tournament is the real test)
