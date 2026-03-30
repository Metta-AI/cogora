# Learnings — 2026-03-30-010306

## Tournament Result Analysis (v496-v508 vs v34, v49, v54)

### Best Variants by Team Size (vs v54 — strongest tested opponent)
- **2a: TV136 ultra-fast** (14.59) — both agents align from step 1, partner handles economy
- **4a: TV82 original** (12.21) — slightly better than TV137's faster start (11.97)
- **6a: TV135 faster ramp** (16.00) — lower min_res thresholds for more aligners earlier

### TV138 (v502) is Overall Best
- Combined TV136 2a + TV137 4a + TV135 6a = avg 14.01-14.19
- However, TV143 (v507) should be even better: TV136 2a + TV82 4a + TV135 6a

### Key Insight: Faster 4a Start is Opponent-Dependent
- TV137 faster 4a (step 50, min_res 20): better vs weak opponents (v34, v49)
- TV82 original 4a (step 100, min_res 30): slightly better vs strong opponents (v54)
- Difference is small (11.97 vs 12.21) — within noise

### Carbon Bottleneck in 4a
- Match log analysis: in 4v4, carbon is always the limiting resource
- Hub carbon drops to 11 by step 500 → stuck at 1 aligner
- 2nd aligner doesn't activate until step ~800 when min_res crosses 30
- TV144 (v508) tests min_res 15 threshold — should get 2nd aligner by step ~400

### Self-Play is Poor Tournament Predictor
- Self-play (8v0): TV139 blitz = 6.40 (best), TV137 = 6.02, TV133 = 5.38
- Tournament: TV138/TV143 > TV137 > TV139 (blitz too aggressive)
- Self-play correlation: ~50% — use for validation only, not optimization

### Economy Support for 2a (TV140) Fails
- v504 (TV140) 2a = 7.45 vs v49 — dual aligning (14.14) is 2x better
- Direct junction contribution beats indirect economy support

### Stagnation Analysis
- Score peaks at step 500 (14-20 junctions), then Clips NPC declines it
- By step 2000, most agents in stagnation mode (80% scrambling)
- Late game (step 5000+) contributes very little to overall score
- Early expansion is everything — every early junction-tick matters

### Cooperative Scoring Confirmed
- Both teams get same score (shared cogs network)
- Scrambling = against Clips NPC only, can't scramble partner
- Both human players are cogs, Clips is the enemy

## Qualifying Scores
- v506 (TV142 — 50% stag scramble): 13.59 (best qualifying!)
- v503 (TV139 — blitz): 11.60, 12.91
- v505 (TV141 — faster 4a step 30): 11.17
