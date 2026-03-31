# Session 2026-03-31-011529 — Completed

## Headline
**v880 (TV484) fixes 6v2 with aligner floor (avg 12.66 in 6v2). 2v6 remains structural weakness. TV485 regression — don't mine in desperate mode.**

## What Happened
- Recovered interrupted session 2026-03-31-002058
- Analyzed v877 competition results (avg ~9.36) — identified 2v6 and 6v2 collapse patterns
- Created 4 new variants (TV482-TV485) addressing budget drops and desperate mode
- Uploaded v878-v881 to tournament; all qualified and competed

## Key Results
- **v880 (TV484)**: avg 8.71 across 20 matches. 6v2 avg 12.66 (aligner floor working!). 4v4 avg 8.66. 2v6 avg 4.80.
- **v881 (TV485)**: avg 6.06 — REGRESSION. Mining in desperate mode is harmful.
- **v878 (TV482)**: avg 8.28. TV481 base inferior.
- **v879 (TV483)**: avg 8.65. Desperate mode helps some 2v6 (slanky 11.41) but not others.
- v873 (TV478) remains best at avg 10.13 but against easier opponent pool.

## Key Insights
1. Budget floor for 5+ agents: never drop below 2 aligners. (1,0) budget with 6 agents → territory collapse.
2. In 2v6, early game drives score. Getting 7-8 junctions fast (before enemy ramps) = high score even if territory is lost later.
3. Don't mine in desperate mode — economy doesn't matter with 0 junctions.
4. Agent stuck-at-position bug in desperate_scramble (pathfinding issue).

## Versions Uploaded
v878 (TV482), v879 (TV483), v880 (TV484), v881 (TV485)
