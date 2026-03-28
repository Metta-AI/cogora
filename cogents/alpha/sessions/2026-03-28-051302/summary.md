# Session 2026-03-28-051302 — Summary

**Status**: Completed

## Key Results
- Discovered tournament uses variable team sizes (2+6, 6+2, 4+4)
- Created team-aware policy: 4x better at 4 agents (0.55→2.71)
- Removed bad targeting changes (network/hotspot penalty) — local avg 3.89→5.03
- v155 (v65 replica + deposit12) leads recent versions at 2.19 (25 matches)
- Goal of >10 likely requires fundamentally different approach

## Uploads (v145-v161)
- v145: bias-only (1.99), v146: double scramble (1.87), v147: super aggro (2.01)
- v148: 3 scramblers (1.35), v149: no scramble (1.91)
- v150-v156: v65 replica variants (1.78-2.19)
- v157: econ-first (2.10), v158-v161: v65 replica + team-aware budgets

## Key Insight
v65's 3.24 score is historical (played weaker opponents). Current competitive pool
yields ~2.0-2.2 for all versions. Improvement requires team-size adaptation and
better competitive strategy, not v65 replication.
