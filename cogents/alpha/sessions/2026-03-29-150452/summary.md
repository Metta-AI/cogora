# Session Summary — 2026-03-29-150452

## Objective
Iterate on TV25 (v388, #1 at 12.38) to find improvements, and check v406/v407 tournament results.

## Key Results
- **v410 (TV50) = NEW #1 at 12.69** (48 matches) — lower scramble threshold (7 vs 14)
- **v414 (TV53) = #2 at 12.57** (49 matches) — TV46 targeting + 70% scramble
- Both consistently beating v388's 12.38

## Work Done
1. Created 8 new policy variants (TV47-TV54) testing scramble parameters
2. Self-play tested all variants (TV48/TV51 best locally)
3. Uploaded all to tournament (v408-v415)
4. Monitored tournament convergence over ~50 matches each
5. Discovered self-play is anti-correlated with tournament for these changes

## Policies Uploaded
- v408 = TV48 (70% scramble): 11.75
- v409 = TV47 (earlier stagnation): 12.03
- v410 = TV50 (lower scramble threshold): **12.69** ← NEW #1
- v411 = TV49 (100% scramble): 9.05
- v412 = TV51 (70% + earlier): 11.79
- v413 = TV52 (dedicated scrambler): 8.59
- v414 = TV53 (TV46 + TV48): **12.57** ← #2
- v415 = TV54 (TV46 + TV51): 11.95
