# Learnings — 2026-03-30-031321

## Self-play Statistical Analysis (5 runs, 2000 steps, 8v0)

| Policy | Avg Score | Scores | Key Feature |
|--------|-----------|--------|-------------|
| TV142 (baseline) | 1.94 | 2.05, 2.08, 1.91, 1.98, 1.70 | 50% stag scramble, gradual 6a |
| TV162 (lower 6a thresholds) | 1.85 | 2.16, 2.26, 1.13 | 25/40/80 vs 30/50/100 |
| TV159 (30% stag scramble) | 1.61 | 2.64, 0.00, 2.19 | High variance |
| TV163 (adaptive scramble) | 1.61 | 1.69, 1.69, 1.22, 1.75, 1.70 | Consistently worse |

## Critical Insights

### 1. Forced Exploration in Stagnation is Essential
TV163 (adaptive scramble) performed 17% worse than TV142 because:
- The world model remembers all known enemy junctions, even distant ones
- `_preferred_scramble_target()` always returns a target from the world model
- So "adaptive" scramble → nearly 100% scramble → no exploration
- TV142's `step % 200 < 100` FORCES exploration regardless of known targets
- This is essential to discover new neutral junctions during stagnation

### 2. Carbon-Weighted Mining is Counterproductive
- Aligner costs carbon:3, so carbon seems like the bottleneck
- But overweighting carbon causes silicon to become the bottleneck
- Silicon drops below carbon by step 1000 in self-play
- The existing `resource_priority` (sort by lowest inventory) is already adaptive
- It automatically shifts mining priority as bottlenecks change

### 3. TV142's Conservative Economy Ramp is Critical
- TV142 6a: 10→30→50→100 thresholds for 1→2→3→4→6 aligners
- TV154 6a: 4 aligners immediately from step 30
- TV142 = 14.30 in tournament, TV154 = 13.76 (0.54 behind)
- Aggressive 6a depletes resources → aligners can't sustain hearts
- The gradual ramp keeps economy healthy for sustained alignment

### 4. Self-play Variance is Extremely High
- Individual games can score 0.00 (wipeout) to 2.64
- Need 5+ runs for any meaningful signal
- Self-play to tournament correlation is ~50% at best
- Tournament is the only reliable measure

### 5. Leaderboard Confirmed Hierarchy
- 50% stag scramble: +0.1-0.3 points consistently
- Conservative 6a: +0.54 over aggressive 6a
- TV142 at 14.30 may be near the heuristic ceiling

## Uploads and Expected Results
- v517: TV156 ultimate combo — baseline comparison
- v518: TV159 (30% stag scramble) — test if less scramble is better
- v519: TV160 (faster stagnation) — test earlier detection
- v520: TV157 (aggressive 6a) — expected worse (confirmed in self-play)
- v521: TV161 (carbon mining) — expected worse (confirmed in self-play)
- v522: TV162 (lower 6a thresholds) — most promising, matches TV142 in self-play
- v523: TV163 (adaptive scramble) — expected worse (confirmed in self-play)
