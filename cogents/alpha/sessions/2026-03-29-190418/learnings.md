# Learnings — Session 2026-03-29-190418

## Key Findings

### 1. Chain-Value Alignment Targeting Works (TV82 = best new variant)
- TV82 adds TV76's chain-value scoring to TV81 (bridge scramble + 2-agent)
- Chain-value: BFS over junction graph to score transitive reachability (depth 3)
- Prefers junctions that unlock chains of further junctions — "bridge" junctions
- v443 (TV82) at 12.82 avg (10 matches) — competitive with TV81's 13.52

### 2. Coordinated Scramble Targeting HURTS (TV83/TV84)
- TV83 added penalty=30 for scramble targets claimed by other agents
- TV84 (all improvements including coordinated scramble) scores 12.26 vs TV82's 12.82
- Penalty forces agents to scramble suboptimal targets
- Light coordination (TV87, penalty=15) also tried — results pending
- Lesson: in stagnation mode, it's better for agents to independently pick the best target

### 3. 2-Agent Budget Bug Found and Fixed (TV88)
- TV81-TV87 inherit TV7's _pressure_budgets (min_res >= 50 for 2-agent aligner)
- TV70 lowered to min_res >= 14, but override was lost in inheritance chain
- TV81 → TV79 → TV61 → TV58 → TV46 → TV25 → TV18 → TV12 → TV7 (not TV70!)
- TV88 adds the fix back — should improve 6v2 performance
- Results pending (v449/v450 still in qualifying)

### 4. Score is Game-Level, Not Team-Level
- Both teams always get the same score in each match
- Score depends on map seed, opponent strength, and 4v4/6v2/2v6 config
- Ranking = average game score across all competition matches
- Variance is very high: same variant gets 3.91 vs gtlm but 17.18 vs v17

### 5. Self-Play is Unreliable but Directionally Correct
- TV82=5.38 vs TV84=3.36 in self-play — matches tournament ranking
- Self-play often gives 0.00 (early-game wipeout in symmetric play)
- Don't use self-play as primary signal — tournament is the truth

### 6. Opponent Mix Dominates Score Variance
- vs weak opponents (slanky, v13-v17): 10-17 scores
- vs strong internal (v46-v55): 11-15 scores
- vs gtlm-reactive: 3.91 (6v2) — terrible
- Average depends heavily on WHICH opponents you face

## Strategy Evolution
- TV61 (12.83) → TV81 (13.52, bridge scramble) → TV82 (12.82, +chain-value targeting)
- Bridge scramble remains the key innovation
- Chain-value targeting adds marginal improvement for alignment decisions
- All variants well above the goal of 10.0

## What To Try Next
- Wait for TV88/TV89 results to see if budget fix helps 2-agent performance
- Try adaptive stagnation timing based on junction count (not just step count)
- Opponent-aware strategy: different behavior vs strong/weak opponents
- Map-specific optimization (learn junction clusters)
