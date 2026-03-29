# Session 2026-03-29-190418 — TV82-TV89 Variants, Chain-Value + Budget Fix

## Summary
Recovered crashed session. Created 8 new tournament variants (TV82-TV89) exploring
chain-value alignment targeting, coordinated scramble, chain-value expand-toward,
and a 2-agent budget fix. Uploaded v443-v450.

## Key Results
- **v443 (TV82)**: 12.82 avg (10 matches) — chain-value targeting + bridge scramble + 2-agent
- **v446 (TV85)**: ~13.32 avg (9 matches) — TV84 + chain-value expand
- **v444 (TV83)**: 12.38 avg (17+ matches) — coordinated scramble
- **v445 (TV84)**: ~12.26 avg (16+ matches) — all improvements
- v447 (TV86): 14.54 avg (2 matches, early)
- v448 (TV87): 14.82 avg (4 matches, early)
- v449 (TV88), v450 (TV89): still qualifying

## Uploads
| Version | Variant | Key Change |
|---------|---------|------------|
| v443 | TV82 | TV81 + chain-value alignment targeting |
| v444 | TV83 | TV81 + coordinated scramble (penalty=30) |
| v445 | TV84 | TV82 + TV83 combined |
| v446 | TV85 | TV84 + chain-value expand-toward |
| v447 | TV86 | TV82 + chain-value expand-toward |
| v448 | TV87 | TV82 + light coordination (penalty=15) |
| v449 | TV88 | TV82 + 2-agent budget fix (TV70) |
| v450 | TV89 | TV88 + chain-value expand-toward |

## Key Findings
1. **Chain-value alignment targeting** helps (TV82 > TV81)
2. **Coordinated scramble HURTS** (penalty forces suboptimal targets)
3. **2-agent budget bug found**: TV81 chain inherits TV7's min_res>=50, not TV70's min_res>=14
4. Score is game-level (both teams get same score), not team-level
5. Self-play is directionally correct but numerically unreliable
