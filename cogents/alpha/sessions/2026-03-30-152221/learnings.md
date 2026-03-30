# Learnings — Session 2026-03-30-152221

## Key Findings

### Heuristic Ceiling at ~14.94
- After 700+ variants tested, the heuristic policy ceiling is confirmed at 14.94 (v632, TV272).
- All parameter tuning converges to 14.6-14.9 with 30+ matches.
- Early match scores (4-10 matches) are extremely noisy and unreliable — always wait for 30+ matches.

### Re-align Bonus (hotspot weight)
- Negative hotspot weight (prioritize re-aligning scrambled junctions) provides marginal benefit (~0.1-0.2).
- All weights tested (-4, -8, -12, -16) converge to similar scores (14.65-14.88).
- Not a game-changer but consistently positive.

### 7th Aligner Threshold
- 7a@150 (TV272, v632) = 14.94 — best
- 7a@120 (TV334, v696) = 14.82 — slightly worse
- 7a@100 (TV277, v637) = 14.62 — worse
- The 7th aligner costs too much economy at lower thresholds.

### What Doesn't Work
- **Hub-proximity scramble** (TV322): restricting scramble to hub range = 11.86. Too limiting.
- **Faster aligner ramp** (TV323): earlier 3rd/4th aligners = 13.24. Economy can't sustain.
- **No stagnation scramble** (TV325): = 2.08. Stagnation scramble is ESSENTIAL.
- **Mine during stagnation** (TV329/TV330): = 10.0/9.9. Exploring during stagnation finds neutral junctions.
- **Wider scramble windows** (TV327/TV328): = 13.93/14.35. More scrambling wastes hearts.
- **Bottleneck scramble** (TV305/TV335): wastes HP traveling to distant enemy junctions.

### Fundamental Issue
- Clips AI gradually takes all junctions by step 3000 in qualifying.
- Score is determined by early game (steps 0-2000) when we hold 10-15 junctions.
- All optimizations are within the 14.6-14.9 band because the fundamental dynamics are the same.
- To break through, need a completely different approach (LLM cyborg, opponent modeling, etc.)

### World Model Stale Data
- Each agent has its own world model (not shared across team).
- Agent-reported "friendly_j" count includes stale data from junctions observed earlier but since scrambled.
- This means friendly_j overestimates true junction count, especially for agents that stay in one area.

## Tournament Stats
- Top 310 positions are all alpha.0 variants.
- Best non-alpha: slanky at 6.32 (#311), Paz-Bot at 6.25 (#312).
- Massive competitive advantage — even worst variants beat all opponents.
