# Session Learnings: 2026-03-29-200453

## Key Findings

### 1. Tournament Scores are Game-Level (Shared Between Teams)
Both teams in a match ALWAYS get the same score, even against external opponents.
Score = "avg aligned junctions in team network per tick" but it's a game-level metric.
This means scrambling hurts both teams' scores equally.

### 2. Zero-Scramble Fails Qualifying
TV94/TV95 (zero scramble) scored 2.0-2.5 in qualifying — catastrophic. The qualifying
opponent scrambles our junctions; without scrambling back, junctions collapse permanently.
Scramble defense is ESSENTIAL for qualifying.

### 3. min_res >= 7 for 2-Agent is a Marginal Win
TV90 (v451) lowered the 2-agent aligner threshold from min_res >= 14 to >= 7.
Early data showed 13.87 (10 matches), converged to 12.83 (36 matches).
The improvement is real but small: 2v6=11.29 vs baseline 11.00.

### 4. Reduced Heart Batch Kills 2v6
TV91 (reduced heart batch to 2 for 2-agent) and TV93 (early aligner step 100)
both caused 2v6 scores to crash from ~11 to ~5.4. Extremely toxic changes.
Heart batch of 3 and step 200 threshold are critical for 2-agent survival.

### 5. 4v4 Scores are Heavily Opponent-Dependent
Same-version policies give identical 4v4 scores against the same opponent.
Scores range from 10.04 (vs v31) to 17.18 (vs v11-v17). The map/seed
determines most of the score variance, not the policy.

### 6. Self-Play Poorly Predicts Tournament
Self-play at 5K/10K steps shows very different patterns from tournament.
Tournament scores depend on opponent mix. Always validate in tournament.

### 7. Faster Stagnation Detection Hurts
TV100 (200-step stagnation vs 300-step) scored 11.45 (27 matches) — significantly
worse than baseline. The 300-step threshold is well-calibrated.

### 8. 3 Aligners in 4v4 Slightly Hurts
TV99 (3 aligners instead of 2 in 4v4) scored 12.40 (30 matches) vs 12.83 baseline.
The economy can't sustain 3 aligners with only 1 miner.

## Tournament Ceiling
Current heuristic approach seems to hit a ceiling around 12.8-13.0 across all
variants tested. Breaking through likely requires:
- RL training (needs GPU)
- Fundamentally different strategies (not tested)
- Better map exploitation (understanding scoring formula)
