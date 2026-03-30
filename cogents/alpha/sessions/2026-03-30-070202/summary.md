# Session 2026-03-30-070202 — Summary

## Key Achievement: v550 (TV194) = Best New Variant (avg ~15.1)

Created 10 new policy variants (TV192-TV201, v548-v557). v550 (TV194) is
the strongest, consistently scoring 13.8-16.8 across all configurations.

## Uploaded v548-v557 (10 versions)

| Version | Policy | Avg Score | Notes |
|---------|--------|-----------|-------|
| v550 (TV194) | TV186+faster 4a | ~15.1 | Best new — min_res 15 sweet spot |
| v555 (TV199) | TV186+reactive defense | ~14.8 | Good vs aggressive opponents |
| v557 (TV201) | TV162 6a+TV186 stag+TV198 4a | qualifying | Best predicted combo |
| v554 (TV198) | TV186+always 2 aligners 4a | ~14.4 | Stable 4a economy |
| v556 (TV200) | TV192 6a+TV186 stag+TV198 4a | qualifying | May have 6a weakness |
| v548 (TV192) | Even lower 6a thresholds | ~14.0 | 6a too aggressive |
| v553 (TV197) | Ultra-fast 4a (min_res 10) | ~14.3 | 4v4 crashes |
| v552 (TV196) | Aggressive 2a | — | Similar to TV162 |
| v551 (TV195) | Adaptive scramble | ~13.0 | Bad |
| v549 (TV193) | Scramble-on-sight | ~8.4 | Terrible |

## Key Findings

1. **min_res 15 is optimal for 4a** (v550 > v542 > v553)
2. **TV192's 6a thresholds (20/30/60) hurt** — TV162 (25/40/80) proven better
3. **Scramble-on-sight is terrible** (v549 = 8.4 avg)
4. **3 new opponents discovered**: gtlm-reactive-v3, slanky:v112, Paz-Bot-9005
5. **Anti-opponent performance is weak** — 7-14 vs external, 14-16 vs alpha

## Leaderboard Status

Goal of >10 was achieved in prior sessions (v522=15.00).
Current expected leaderboard: v522 #1 (14.41), v542 #2 (14.39).
v550 and v557 could push to #1 with 4a improvement.
