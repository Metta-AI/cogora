# Learnings — 2026-03-30-040613

## Critical Finding: Idle Scramble is ESSENTIAL

The biggest discovery this session: removing idle scramble costs ~1.2 tournament points.

| Policy | Idle Scramble | Tournament Score | Matches |
|--------|:---:|:---:|:---:|
| v519 (TV160) | Yes | 13.99 | 67 |
| v526 (TV166) | No | 12.77 | 38 |
| v527 (TV167) | No + 25% stag | 12.69 | 38 |
| v528 (TV169) | None at all | 3.02 | 38 |

**Why idle scramble helps in cooperative scoring**: Junction recycling. Scrambling enemy
junctions creates neutral junctions that can be re-aligned. This generates more alignment
events over time, increasing the per-tick average. Without idle scramble, the game
stagnates once all nearby neutrals are claimed.

## Self-play is MISLEADING

The most dangerous finding: self-play results do NOT predict tournament performance.

| Policy | Self-play (2K, 4 runs) | Tournament |
|--------|:---:|:---:|
| TV166 (no idle) | 2.13 avg (BEST, very consistent) | 12.77 (WORST) |
| TV160 (baseline) | 1.76 avg (worse, high variance) | 13.99 (BEST) |
| TV170 (boundary + no idle) | 2.32 avg (2nd best) | 10.18 (BAD) |

Self-play rewards consistency and penalizes idle scramble (since both teams scramble each other).
But tournament rewards junction turnover from idle scramble. **NEVER trust self-play for
strategy decisions** — always validate in tournament.

## Optimal Scramble Amount: 50%

| Stag Scramble % | Best Version | Tournament |
|:---:|---|:---:|
| 0% | v528 (TV169) | 3.02 |
| 25% | v527 (TV167) | 12.69 |
| 50% | v519 (TV160) | 13.99 |
| 75% | TV176 (not uploaded) | wipeouts in self-play |

## Score Depends on Opponent Strength (cooperative scoring)

Both teams always get the same score. Playing against strong opponents (other alpha versions)
gives 14-17 points. Playing against weak opponents (gtlm) gives 4-11 points.

v525 (68 matches) score breakdown:
- vs gtlm (weak): 4.43 (2a vs 6a)
- vs alpha v11-v17: 15-17
- vs alpha v30-v53: 12-15

The score is determined ~50% by opponent quality, not just our policy.

## Heuristic Ceiling at ~14.0

Top 4 converged versions (67-68 matches each) are all within 0.21 points:
1. v519 = 13.99
2. v525 = 13.84
3. v524 = 13.79
4. v522 = 13.78

The differences between stagnation timing, 6a thresholds, and combo approaches
are marginal. The heuristic approach has likely reached its ceiling.

## What Was Tested (and didn't help)

- **No idle scramble** (TV166-TV170): -1.2 points
- **Zero scramble** (TV169): -11 points
- **75% stag scramble** (TV176): wipeouts
- **Zone-based exploration** (TV173): high variance, avg 1.90 self-play
- **Faster 4a ramp** (TV171): economy collapse
- **Faster 6a ramp** (TV168): economy collapse (1.00 self-play)

## Still Qualifying (need more data)

- v531 = TV174 (boundary scramble + keep idle) = 10.96 (2 matches)
- v532 = TV175 (earlier heart batching)
- v533 = TV177 (lower 6a threshold, min_res 80)
- v534 = TV178 (2a mining burst first 50 steps)

## Suggestions for Next Session

1. Wait for v531-v534 tournament results to converge
2. Consider RL training — heuristic ceiling confirmed at ~14.0
3. Look into the LLM cyborg policy (AnthropicCyborgPolicy) for potential gains
4. Study opponent logs more carefully to find unexploited strategies
5. The 2a config is the biggest scoring bottleneck (12-13 vs 15-16 for 6a)
