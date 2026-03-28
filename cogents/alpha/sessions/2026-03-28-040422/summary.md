# Session 2026-03-28-040422 — Summary

**Status**: Completed

## Key Results
- v65 remains #1 at 3.24 (321 matches) — base SemanticPolicy
- v140 best recent at 2.66 (23 matches)
- Discovered: local self-play does NOT predict tournament performance
- All "improvements" since v65 era are net negative in tournament

## What Was Tried
- Stable budgets (v135): fixed role oscillation, +34% single-seed, but -40% multi-seed vs v134
- Hotspot avoidance (v137): ship zone detection, moderate local improvement
- A/B base vs alpha: base 2.68 local / 3.24 tournament, alpha 3.25 local / ~2.0 tournament
- Uploaded v134-v143 to tournament (various combinations)

## Key Insight
Tournament is alpha-vs-alpha — our versions compete against each other. The simpler
base policy (v65) outperforms optimized variants in head-to-head competition, even
though optimized variants score higher in local self-play against clips ships.

## Next Steps
- Study v65 code to understand what makes it competitive
- Focus on tournament-relevant testing (opponent matchups, not self-play)
- Consider reverting to base policy with minimal, targeted improvements
- Monitor v143 (base policy reupload) tournament results
