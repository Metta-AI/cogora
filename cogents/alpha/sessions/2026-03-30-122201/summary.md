# Session Summary — 2026-03-30-122201

## Outcome
Created 16 tournament variants (TV263-TV276, v622-v636). Best new variant:
v632 (TV272) = **NEW #1 at 15.17** (24m), up from 14.82.

## Key Discovery
**Combining ALL proven features** — TV208 base + early aligner + decaying peak
+ adaptive scramble + 7 aligners at high resources — produces the best overall
policy. Each feature contributes incrementally, and they don't interfere.

## Variants Uploaded (16 total)
| Variant | TV# | Score | Matches | Result |
|---------|-----|-------|---------|--------|
| v632 | TV272 | 15.17 | 24 | **Session best, NEW #1** |
| v625 | TV266 | 14.98 | 24 | #2 |
| v623 | TV264 | 14.97 | 24 | #3 |
| v628 | TV269 | 14.92 | 24 | #4 |
| v624 | TV265 | 14.58 | 24 | Moderate |
| v626 | TV267 | 14.56 | 24 | Moderate |
| v636 | TV276 | 14.52 | 10 | Settling |
| v622 | TV263 | 14.44 | 24 | Moderate |
| v629 | TV270 | 13.53 | 24 | Bad |
| v635 | TV275 | 13.49 | 13 | Bad |
| v631 | TV271 | 12.61 | 24 | Bad (capture scramble) |
| v633 | TV273 | 11.18 | 22 | Bad (capture on TV264) |
| v627 | TV268 | 11.98 | 24 | Bad (skip idle scramble) |
| v634 | TV274 | 10.96 | 24 | Bad (kitchen sink w/ capture) |

## What Failed
- Capture-optimized scramble targeting: TOXIC everywhere (10-12 range)
- Skipping idle scramble when ahead: CATASTROPHIC (11.98)
- Earlier 4th aligner / lower thresholds: Too aggressive
- Faster stagnation on TV264 base: Decay already handles timing
