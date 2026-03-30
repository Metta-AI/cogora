# Session Learnings — 2026-03-30-212420

## Key Discoveries

### 1. Aligner Floor Prevents Death Spiral (TV452-TV454)
When resources drop low, TV350's budget reduces aligners to 1.
This causes a death spiral: fewer aligners → lose junctions → economy stress → stays at 1 aligner.
**Fix**: Floor of 3 aligners for 5+ agents (only after step 100 to preserve initial economy).
- TV350 6a: 1.26 → TV454 6a: 1.74 (+38% locally)
- v840 (TV454) avg 10.75 in competition vs opponents

### 2. TV436 Base Was Wrong — TV350 Is the Proven Winner
TV440-TV446 (v826-v832) built on TV436 base, not TV350.
TV436's 2-agent economy changes hurt common 6v2/4v4 matchups.
v831/v832 avg 6-8 in competition vs v716's 15.05.
**Lesson**: Always build new variants on the proven best base (TV350).

### 3. Faster 4a Ramp (can_hearts → 2 aligners)
4-agent teams get stuck at 1 aligner when min_res < 15 (TV350).
Fix: ramp to 2 aligners when can_hearts=True (all resources ≥ 7).
v840 vs v841: 10.75 vs 7.60 — the 4a ramp alone adds +3.15 avg.

### 4. Budget Scramblers HURT Performance
v851-v852 (with budget scramblers) scored worse than v840 (without).
- v840 6v2 vs lstm=8.99 vs v851 6v2 vs lstm=7.87
- v852 4v4 vs lstm=0.80 (terrible with scramblers)
**Lesson**: Scramblers work as idle aligner behavior, NOT as dedicated budget.
TV350 (v716=15.05) also used no budget scramblers.

### 5. Early-Game Floor Bug
Applying aligner floor at step 1 drains initial hub resources on hearts.
Hub starts with num_agents*3 of each resource. Hearts cost 7 each.
3 hearts = 21 resources, leaving ~3 = can't gear miners.
**Fix**: Only apply floor after step 100 (economy bootstrap).

### 6. 2v6 Matchups Are Fundamental Weakness
With only 2 agents, we can't control the team economy.
If teammate (mammet, gtlm-reactive) is bad, total score tanks.
2v6 scores: 0.18-11.91 range — huge variance.
Not much we can do here — focus optimization on 6v2 and 4v4.

## Version Map (This Session)
- v837 = TV450 (floor 3, TV350 base)
- v838 = TV451 (crisis + floor 3)
- v839 = TV448 (floor 2, TV350 base)
- v840 = TV454 (floor 3 + faster 4a ramp) ← BEST NEW VARIANT
- v841 = TV452 (floor 3 only)
- v843 = TV455 (uploaded as my kitchen sink)
- v850 = TV464 (TV454 + crisis + scramblers)

## Competition Performance Summary (avg non-self score)
- v716 (TV350): 15.05 — current overall #1
- v840 (TV454): 10.75 — best new variant (9 matches)
  - Without 2v6 gtlm outlier: 12.45
- v841 (TV452): 7.60
- v838 (TV451): 7.76
- v832 (TV446): ~8.04
- v831 (TV445): ~6.07

## Next Steps
1. Understand why v716 scores 15.05 but v840 only 10.75 — is it match distribution?
2. Optimize 2-agent performance (mining efficiency, faster heart acquisition)
3. Consider RL training if heuristic ceiling is truly ~15
