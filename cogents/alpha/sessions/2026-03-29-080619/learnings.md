# Learnings — Session 2026-03-29-080619

## Discovery: Junction Discovery is THE Bottleneck
Game analysis shows junction count plateaus at step 1000 (~21/65 junctions found)
on a 88x88 map with 13x13 observation window. Agents can't see junctions they
haven't visited. Late-game decline (21→12 friendly junctions, steps 1000→5000) is
primarily caused by inability to find new junctions, not economy failure.

## Discovery: Idle Exploration Beats Idle Mining
TV7's idle behavior alternates explore/mine, scoring 5.38 (8a/5K).
Pure explore idle (no scramble) scored 2.88 — Clips dominates without scramble pressure.
The key: idle scrambling is CRITICAL, but mine-only idle wastes potential junction discovery.

## Discovery: Idle Step Counting is Best Exploration Trigger
Three exploration triggers tested:
1. **Junction count stagnation (TV12)**: Track peak friendly junctions, trigger after 300 steps of no growth. Works well in self-play but hurt tournament (7.5 vs 8.6 for TV9). May trigger too aggressively with mixed teams.
2. **Idle step counting (TV15)**: Count consecutive steps with no align target available. After 150 idle steps, enter full-map exploration. Self-play avg 15.16 — best result. Simpler and more robust.
3. **Always-explore (TV9-variants)**: Lost to Clips due to no scramble pressure.

## Discovery: Self-Play ≠ Tournament
TV12 scored 9.9 avg in self-play but only 7.5 in tournament (12 matches).
TV9 scored ~5 in self-play but 8.61 in tournament.
Tournament has variable team sizes (2/4/6 agents) and different opponents.
Self-play (8 agents, same policy) is a poor predictor of tournament performance.

## Discovery: Map Layout Variance is Massive
Same policy, different random seeds: scores range from 0.00 (wipeout) to 36.11.
Map layout (junction placement relative to hub) is the dominant factor.
Can't control this — must optimize average performance across map types.

## Discovery: Economy Bottlenecks
- Silicon has fewest extractors (45 vs 50-58 for others)
- Silicon runs out first, killing heart production
- Miners mine wrong resource when they haven't discovered silicon extractors
- More scramblers crash economy (TV10: 3.55 — doubled scramblers collapsed hearts)
- Carbon and germanium hoard to 1000+ while silicon hits 80

## Discovery: Chain Push Works
After aligning a frontier junction (>15 from hub), continuing 15 steps in
that direction discovers more junctions along the chain. TV11b added +~10%
over TV9 baseline (self-play).

## Architecture Summary
Best policies combine:
1. TV7's 2-agent mining (mine for 500 steps, only align when min_res>=50)
2. TV9's 2-agent timing fix (align at step 200 instead of 500)
3. TV15's idle step counter → full-map exploration after 150 idle steps
4. Chain push after frontier alignments
5. AdaptiveV3/Balanced economy budgets with team cap

## What Didn't Work
- TV8 wide explore (1.19) — agents go too far, die
- TV10 double scramble (3.55) — economy collapse from extra hearts consumed
- TV9-explore (2.88) — no scramble = Clips dominates
- TV12 stagnation in tournament (7.5) — too aggressive in mixed teams
