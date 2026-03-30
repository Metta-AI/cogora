# Session Summary — 2026-03-30-221202

**One-line:** TV350 base is sacred — all modifications regress; v847 (TV462, TV350-preserving) scored 13.59 closest to v716's 15.05.

## Key Actions
- Found zero-scrambler issue in TV452+ → discovered TV350/v716 ALSO has zero scramblers (by design)
- Created TV455-TV466 (14 variants): scrambler fixes, floor variants, stag scramble, small-team fixes
- Uploaded v842-v854 (13 uploads) to tournament
- Analyzed competition results: v847 (TV462, preserving TV350 for 5+) best at 13.59 vs Paz
- Aggressive stag scramble (TV466) hurts: avg 4.76 across external matches
- Confirmed pattern: any change to TV350's 5+ agent logic regresses from v716's 15.05

## Key Insight
Score = avg aligned junctions per tick. Scramblers don't add to OUR score. TV350 maximizes aligners → maximizes score. The "stag_scramble" opportunistic behavior when idle is sufficient.
