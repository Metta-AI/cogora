# Learnings — 2026-03-30-091114

## v564 (TV208) is the Reliable Best at ~15.0

TV208 = TV207 (6a thresholds 22/35/70) + TV206 (3-tier stagnation).
No 4a changes. Stable at 14.96 with 18 diverse matches.

v566 (TV210 = TV209 + step<30) briefly overtook at 15.09 (18m), but the
difference is within noise. The 4a changes provide marginal benefit at best.

## 4a Aggressive Changes are Unreliable

Early results (3-6 matches) showed 4a improvements (min_res 12, step<30,
3rd aligner 60/200) scoring 15-16+. With 18 matches, scores dropped to
14.3-14.6. The 4a changes work well vs weak opponents but hurt vs strong
ones by diverting mining resources too early.

| Variant | Description | Score (18m) | vs v547 |
|---------|------------|------------|---------|
| v566 (TV210) | step<30 4a | 15.09 | +0.40 |
| v564 (TV208) | no 4a changes | 14.96 | +0.27 |
| v567 (TV211) | 3rd aligner 60/200 | 14.77 | +0.08 |
| v568 (TV212) | full 4a combo | 14.55 | -0.14 |
| v565 (TV209) | min_res 12 + 6a | 14.30 | -0.39 |

step<30 is the only 4a change that might help. All others are negative.

## Stagnation Modifications are CATASTROPHIC

Any modification to the stagnation cycle destroys performance:
- v574 (TV218, full scramble when no neutrals): 10.75
- v576 (TV220, fast stag + smart stag): 9.62
- v573 (TV217, phase-based budgets): 12.86
- v571 (TV215, reduced aligners): 13.50
- v572 (TV216, heart hoard): 14.16
- v575 (TV219, fast 6a stag + step<30): 14.35

The 50% scramble/explore cycling in stagnation is essential. The explore
phase finds new junctions even when we think they're all owned — agents
have limited observation range (13x13) and the map is 88x88.

## 6a Thresholds 22/35/70 are Optimal

Tried tighter (21/33/65) and looser (20/30/60):
- v578 (TV222, 21/33/65): 14.29 (17m) — below baseline
- v570 (TV214, 20/30/60): 14.81→dropped off
- v564 (TV208, 22/35/70): 14.96 (18m) — best

Even small threshold changes hurt. The 22/35/70 values found in TV207
are a precise optimum.

## Early Scores are Highly Misleading

Single-match scores were off by 2-3 points:
- v565: 16.33 (3m) → 14.30 (17m) = -2.03
- v569: 17.32 (1m) → 14.89 (11m) = -2.43
- v564: 16.35 (6m) → 14.96 (18m) = -1.39

Need 15-20+ matches for reliable scores. The qualification matches are
all vs v557 (which scores 9.90), heavily inflating early scores.

## Heuristic Ceiling is ~15.0

The best heuristic policy (TV208/v564) plateaus at ~15.0 with diverse
opponents. The theoretical max is ~32 (half of 65 junctions). We capture
about 47% of what's theoretically possible. Breaking through would require
fundamentally different approaches (RL, better targeting, opponent modeling).

## What to Try Next

1. **Validate v566 vs v564**: Are they truly different or just noise?
2. **Focus on opponent-specific strategies**: gtlm-reactive still drags scores
3. **Consider LLM cyborg policy**: Runtime adaptation might break the ceiling
4. **RL training**: If GPU access becomes available
