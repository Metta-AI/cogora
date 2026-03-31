# Session Summary — 2026-03-31-030250

## Key Results
- Created TV486-TV490 + TV489 variants, uploaded v882-v890
- **v884 (TV488) confirmed best: avg 9.58** — 4v4 aligner floor + 5+ aligner floor
- All modifications to stagnation or budget regressed:
  - v885 (TV489, aggressive scramble): avg 5.90
  - v888 (TV490-alt, faster ramp): avg 6.91
  - v887 (TV491, scorched earth): avg ~4.63
- Heuristic ceiling confirmed at ~10

## Strategy
v884 (TV488) = TV478 (best 2v6 stagnation) + aligner floor for both 4v4 and 5+ agents.
No desperate mode, no stagnation changes. Clean combination of proven features.

## Next Steps
1. RL training — only way to break heuristic ceiling
2. Resource imbalance awareness (v886) — inconclusive, worth retesting
3. LLM-based pre-game strategy adaptation
