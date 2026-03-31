# Learnings — Session 2026-03-31-011529

## Budget Floor is Critical for 6v2
- TV350's "sacred" budget drops to (1,0) for 5+ agents when min_res < 10 and can't refill hearts.
- This means 5 miners, 1 aligner — territory collapses even with 6 agents.
- **Fix**: Never below (2,0) for 5+ agents. Economy recovers with 4 miners just as well as 5.
- v880 (TV484) 6v2 avg: 12.66 (was ~8-12 before).

## Desperate Mode Has Limited Value
- In 2v6 stagnation with 0 friendly junctions, removing min_res check and time window for scramble helps
  some matchups (v878 vs slanky: 13.00) but not others (vs coglet: 2.21, vs gtlm-reactive: 1.19).
- The fundamental 2v6 problem is structural: 2 agents can't hold territory against 6.
- Score is time-averaged, so EARLY GAME drives the result. A 2v6 match where we peak at 8 junctions
  in 500 steps then lose everything can still score 13.00 (vs slanky).

## Don't Mine in Desperate Mode
- TV485 added `not _h.team_can_refill_hearts(state)` check that forces mining when germanium is low.
- This is WRONG — mining is pointless with 0 junctions. Should scramble to reclaim territory.
- TV485 avg 6.06 vs TV484's 8.71 — clear regression.

## Agent Gets Stuck at Position
- In desperate_scramble, agent can get stuck at same position for 2000+ steps.
- Likely cause: scramble target is at agent's position (already there) or pathfinding blocked by walls.
- Simple stuck detection (track position, fallback after 150 steps) helps but the mining fallback hurts.
- Better fix: if stuck, pick a DIFFERENT scramble target or explore.

## Expanded Opponent Pool Makes Averages Harder
- Tournament now includes: gtlm-reactive-v3, random-assay-test, swoopy-v0, coglet-v0
- These opponents are tougher, especially in 2v6 matchups.
- v873's 10.13 avg was against a smaller/easier opponent pool.
- v880's 8.71 avg may be comparable when accounting for opponent difficulty.

## Key Variant Hierarchy
1. v873 (TV478): avg 10.13 — always-2-aligners + faster stagnation (best overall)
2. v880 (TV484): avg 8.71 — TV478 + desperate mode + aligner floor (best for 6v2)
3. v878 (TV482): avg 8.28 — TV481 base + desperate mode (inferior TV481 base)
4. v879 (TV483): avg 8.65 — TV478 + desperate mode only (no aligner floor)
5. v881 (TV485): avg 6.06 — regression (mining in desperate mode)
