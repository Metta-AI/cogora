# Session 2026-03-30-051758 — Summary

## Key Finding: Network-Aware Scramble Targeting is Harmful

Created 7 new policy variants (TV179-TV185, v535-v541) testing:
- Network-aware scramble targeting (prefer in-network enemy junctions)
- Higher scramble ratios (75%, always-scramble)
- Faster early expansion (3 aligners at start)
- Adaptive mining (shift to mining when opponent dominates)
- Low scramble thresholds (min_res >= 3)

**Results**: Network-aware targeting drops scores by 3-4 points (11-12 vs 14.5+).
Distance-based targeting is optimal — agents should always scramble the nearest
enemy junction, not travel to in-network ones.

**Best new variant**: v541 (TV185, pure TV160 + faster early ramp) = 13.78 (31m),
rank #11. Faster early expansion helps 4a (+0.68) but hurts 6a (-2.80).

**Leaderboard**: v522=15.00, v525=14.83, v519=14.69 — heuristic ceiling ~14.7-15.0.
All top versions use simple TV142/TV160 behavior with distance-based scrambling.

Uploaded v535-v541 (7 versions). All above goal of >10 except v536 (always-scramble = 7.51).
