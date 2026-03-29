# Session Summary — 2026-03-29-161650

## Goal
Push past v414's 12.63 by combining proven tournament improvements.

## What Happened
Created 11 new variants (TV55-TV65) testing combinations of:
- TV46's reduced hub penalty targeting
- TV50's lower scramble threshold (min_res >= 7)
- TV48's 70% scramble ratio
- Various threshold values (3, 7, 10)
- Earlier stagnation trigger
- Aggressive 2-agent play
- 80% scramble ratio
- Always-scramble idle behavior
- Delayed economy start

Uploaded v416-v426 to tournament. Results at ~50 matches:
- v419 (TV58, kitchen sink) = 12.53 — best new variant
- v421 (TV60, threshold=10) = 12.52
- v416 (TV55, TV46+TV50) = 12.42
- v420 (TV59, TV55+2-agent) = 12.40
- None beat v414 (12.63) or v410 (12.59)

## Key Insight
Improvements are NOT additive. v414 and v410 represent near-optimal
parameter tuning for this architecture. Breaking past 12.6 requires
a fundamentally different approach, not parameter combinations.

## Score: v414 = 12.63 (#1), unchanged from session start
