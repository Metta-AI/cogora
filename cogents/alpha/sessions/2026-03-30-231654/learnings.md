# Session Learnings — 2026-03-30-231654

## Key Discoveries

### 1. Modular-LSTM Scramble Collapse Mechanism
Deep analysis of 6v2 match vs modular-lstm (match 4ec5e0a3):
- We dominate early: 10 friendly junctions at step 1000, enemy has 3
- modular-lstm's 2 RL agents systematically scramble us: 10→1 friendly by step 2100
- Our agents enter stag_scramble→retreat_to_hub oscillation for 8000+ steps
- Root cause at collapse point (step 1500): min_res=6, budget drops to 1 aligner
- Hub resource imbalance: carbon=6, oxygen=47 — one resource bottleneck kills budget

### 2. Budget-Only Changes (TV470/v863) = Best New Variant
TV470 combines reactive budget (boost aligners when behind on junctions) with
aligner floor (never drop below 2 for 5+ agents). Results:
- **4v4 vs modular-lstm: 11.42** (was 0.99 for v851!)
- 6v2 vs Paz-Bot: 14.60
- 6v2 vs gtlm: 14.51
- 4v4 vs Paz-Bot: 11.49
The aligner floor prevents the death spiral where budget drops to 1.

### 3. Recovery Mode HURTS Normal Play
TV471 (hub-focused recovery scramble) and TV472 (combined) performed poorly:
- v861 (TV471) 6v2 vs coglet: 2.24 (terrible!)
- v862 (TV472) 6v2 vs coglet: 4.29
- v869 (TV474 = hub-recovery + lower thresholds) 6v2 vs modular-lstm: 3.40
The recovery mode threshold (peak*0.4 + enemy>2x) triggers too easily and
forces suboptimal scramble targeting even when the game isn't lost.
**Lesson**: Small behavioral changes that seem obviously good in isolation
often hurt aggregate performance because they interact with edge cases.

### 4. Capture-Optimized Scramble HURTS 6v2 Performance
TV475 (v870 = TV470 + capture-optimized scramble targeting):
- 6v2 vs modular-lstm: 6.09 (bad)
- 6v2 vs slanky: 5.87 (bad)
Prioritizing network-adjacent enemy junctions means ignoring strategic targets
further away. The base scramble targeting was already well-tuned.

### 5. Lower Budget Thresholds Also HURT
TV476 (v871 = TV470 + lower thresholds for faster aligner ramp):
- 6v2 vs mammet: 3.48 (terrible!)
Faster aligner ramp means fewer miners, which means less economy.
The original thresholds balanced economy vs alignment well.

### 6. Heuristic Ceiling Still ~15
After 50+ variants tested across sessions, no heuristic change beats v716 (TV350)
at 15.05 average. Individual matchup improvements (like TV470's 11.42 vs modular-lstm)
come at the cost of other matchups. The optimization landscape is flat — you can
shift performance between matchups but can't increase the total.

## Version Map (This Session)
- v860 = TV467 duplicate (junction-reactive budget)
- v861 = TV471 (hub-focused recovery) — BAD
- v862 = TV472 (combined recovery+reactive+floor) — BAD
- v863 = TV470 duplicate (reactive budget + floor) — BEST
- v864 = TV468 duplicate (explore-first idle) — MEDIOCRE
- v865 = TV469 duplicate (aligner floor)
- v870 = TV475 (TV470 + capture scramble) — BAD for 6v2
- v871 = TV476 (TV470 + lower thresholds) — BAD for 6v2

## Next Steps for Future Sessions
1. **RL training remains highest priority** — heuristic ceiling confirmed at ~15
2. **Don't modify TV350 aligner behavior** — it's optimal for average tournament mix
3. **TV470 budget is marginally useful** — helps 4v4 vs modular-lstm specifically
4. **Study mammet:v12** — new version appeared, unknown capabilities
5. **Focus on 4-agent optimization** — most room for improvement in 4v4 matchups
