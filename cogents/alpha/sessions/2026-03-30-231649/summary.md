# Session Summary — 2026-03-30-231649

## What happened
Analyzed match logs, identified economy trap (1-aligner fallback), created 8 new
variants (TV467-TV474). TV473 (lower budget thresholds) performed best: avg 8.71
across 16 competition matches (v866). 15.75 peak in 4v4 vs Paz-Bot.

## Versions uploaded
- v855: TV350 re-upload (proven baseline)
- v856: TV467 (junction-differential reactive budget)
- v857: TV468 (explore-first idle)
- v858: TV469 (aligner floor, never <2 for 5+)
- v859: TV470 (combined reactive+floor)
- v866: TV473 (lower 5+ thresholds) — **BEST** avg 8.71
- v867/v868: TV473 re-uploads (v867 failed server error)
- v869: TV474 (hub-recovery + lower thresholds) — avg 5.58

## Key result
v866 (TV473): avg 8.71 (6v2=11.20, 4v4=10.38, 2v6=6.09) across 16 matches.
Peak: 15.75 (4v4 Paz-Bot). Best 2v6: 12.98 (slanky).
