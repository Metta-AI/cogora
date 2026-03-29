# Session 2026-03-29-010815 — INTERRUPTED

## Summary
Session was interrupted (container died). Key findings before crash:

## Key Results
- **UltraV3 local 8a: 11.47** (peak 20j, best ever local) — chain expansion_weight=20 + Aggressive budgets
- **UltraV3 multi-seed avg: 8.47 (8a), 5.68 (4a)**
- **Tournament: Chain expansion HURTS** — V3 gets ~1.0 in 4v4 vs Aggressive 7.0
- v290 (Aggressive) remains tournament king: avg 6.84, max 8.52

## Key Insight
Chain expansion (expansion_weight=20) gives massive local gains but collapses in tournament.
Local self-play doesn't have opponent pressure that reveals economy fragility.
Aggressive with conservative economy still best for tournament.

## Strategy at Crash
Pivoted back to incremental Aggressive improvements. Uploaded v324 (Aggressive baseline) to confirm.
