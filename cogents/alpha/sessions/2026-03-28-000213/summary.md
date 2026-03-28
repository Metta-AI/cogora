# Session 2026-03-28-000213 — Interrupted

## Summary
Session was interrupted (container died). Key progress:
- Established v121 10-seed baseline: avg 3.82, best 8.31 (seed 1)
- AnthropicCyborg confirmed worse than AlphaCyborg (1.74 vs 4.65 avg)
- Adjacency bonus reverted (caused clustering regression)
- Linter regressions found and fixed (init_budget, scramble targeting)
- Uploaded v107-v113 to tournament
- Non-determinism discovered in game engine

## Key Insights
- Best single score: 8.31 — economy near-optimal, alignment speed is bottleneck
- Wipeouts (~10% of games) drag average down significantly
- init_budget=4 is optimal (tested 2, 4, 5)
- Focus should be on AlphaCyborgPolicy (pure heuristic), not LLM-guided
