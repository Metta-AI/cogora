# Session 2026-03-29-230520 — Summary

## Result
**v495 (TV133) = 12.44 comp avg (#1 with solid data, 44 matches)**

## Key Changes
Created TV123-TV133 (v484-v495). Most failed due to dedicated scrambler bug.
The winner: TV133 = minimal changes from TV82:
1. Dual aligner for 2-agent teams (+5 improvement)
2. Replace dedicated scrambler with extra aligner for 5+ agents (+0.5)
3. Keep 4-agent budget EXACTLY as TV82

## Critical Insights
1. **Cooperative scoring**: both teams get same score (cogs team vs clips NPC).
2. **Dedicated scramblers are harmful**: they steal alignment capacity.
3. **TV82's 4-agent budget is optimal**: don't change resource thresholds.
4. **Dual aligner for 2-agent works**: partner's 6 agents handle economy.
5. **No-scrambler for 6-agent helps**: idle aligners scramble enough.

## Scores by Team Size
- 2a = 11.9 (dual aligner, huge improvement from 6.7)
- 4a = 11.1 (exact TV82, room for improvement)
- 6a = 14.3 (no scrambler, excellent)

## Next Steps
- Investigate 4a=11.1 (lower than expected ~13.5)
- Study gtlm-reactive-v3 (our weakest matchup, 2a=4.64)
- Consider 4a-specific improvements without touching budgets
