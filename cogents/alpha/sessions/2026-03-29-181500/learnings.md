# Learnings — Session 2026-03-29-181500

## v442 (TV81) is the New Leader
- Score: 13.52 avg at 11 matches (vs TV61's 12.83 at 63 matches)
- Configuration: TV79 (bridge-aware scramble) + TV70 (2-agent improvement)
- 4v4 scores: 17.18 (vs v11/v13), 11.25 (vs v29)
- vs slanky: 14.60 (6v2), 11.51 (2v6)
- Still accumulating matches; needs more data to confirm

## Key Innovations This Session

### 1. Chain-Value Expansion Scoring
- Implemented `_chain_expansion_value()`: BFS to count transitive junction reachability (depth 3)
- TV76 (chain-value targeting) and TV78 (chain-value expand-toward only) both scored 14.11 in qualifying
- In competition, TV76 avg 12.06 (10 matches) — lower than expected
- Chain value helps in qualifying (solo) but benefits are muted in competition

### 2. Bridge-Aware Scramble Targeting (TV79)
- When choosing scramble targets, add bonus for enemy junctions that, once neutralized and re-aligned, unlock unreachable neutral junctions
- TV79 scored 3.33 in self-play (best ever) but 12.29 in competition — self-play is anti-correlated
- The bridge scramble concept has merit but needs better calibration

### 3. Adaptive Scramble Ratio (TV77) — FAILED
- Varying scramble % based on junction count vs peak (90/80/60%)
- TV77 scored 9.91 in qualifying — significantly worse than TV61's baseline
- Fixed 80% scramble is better than adaptive; don't mess with this parameter

### 4. Dynamic Stagnation Exit (TV80) — MODERATE
- Reduce scramble % when junction count drops below 80% of peak
- TV80 scored 11.08 in qualifying — worse than TV61
- The stagnation behavior in TV61 is already well-tuned

### 5. TV81: Bridge Scramble + 2-Agent (BEST)
- Combined TV79's bridge-aware scramble with TV70's 2-agent improvement
- Competition avg 13.52 (11 matches) — significantly above TV61 (12.83)
- Strong 4v4 scores (17.18) against weaker opponents
- The 2-agent improvement matters because competition has 6v2 asymmetric matchups

## What Didn't Work
1. **Chain-value targeting**: Expensive computation, marginal benefit in competition
2. **Adaptive scramble**: Any deviation from 80% during stagnation hurts
3. **Chain-value expand-toward**: Made self-play worse; qualifying was same as TV78

## What Worked
1. **Bridge-aware scramble**: Turns scrambling into network expansion, not just offense
2. **2-agent play improvement**: Consistent +0.5 in asymmetric matchups
3. **Combining proven features**: TV81 = TV79 + TV70, both individually good

## Self-Play vs Tournament Correlation
- TV79 self-play: 3.33 (best) → tournament: 12.29 (below TV61)
- TV76 self-play: 1.99 → tournament: 12.06 (below TV61)
- TV78 self-play: 1.18 → tournament: same as TV76 in qualifying
- Self-play against clips ships is STILL anti-correlated with tournament
- The qualifying score (solo vs clips) is a better predictor than self-play

## Score is Per-Game, Not Per-Team
- Both teams always get the same score in competition
- Score = avg aligned junctions in cogs network per tick (game-level metric)
- Variation across games is from map seeds and opponent strength
- 4v4 scores vary most by opponent; 2v6/6v2 are more consistent

## Architecture Insight: 35% Overhead
- Only 25% of agent time is spent on productive tasks (align/scramble)
- 35% is overhead (retreat/heal), 20% searching, 17% mining
- Reducing overhead remains the biggest untapped opportunity
