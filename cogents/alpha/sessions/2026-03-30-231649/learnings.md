# Learnings — Session 2026-03-30-231649

## Key Discoveries

1. **Economy trap causes aligner drought**: In 6v2 games, min_res equilibrium at 16-19
   prevents ramping to 3+ aligners (TV350 needs min_res >= 22). With 4 miners producing
   resources spent on hearts for 2 aligners, the economy can't break out. We peak at
   ~13 junctions then lose them all. Fix: lower thresholds (TV473: 3 aligners at min_res=15).

2. **TV473 lower thresholds outperforms TV350 in 4v4**: v866 scored 15.75 and 12.20
   vs Paz-Bot in 4v4 (TV350 best was ~15). The faster aligner ramp gets territory faster.

3. **2v6 is surprisingly variable**: v866 scored 12.98 and 10.88 vs slanky (2v6!) but
   0.48-2.68 vs other opponents. slanky's 6 agents may be inefficient, allowing our 2
   to compete. Opponent quality matters more than team composition in 2v6.

4. **Combined innovations STILL don't stack**: TV474 (hub-recovery + lower thresholds)
   averaged 5.58 vs TV473's 8.71. The hub-recovery scramble behavior conflicts with
   aggressive alignment. Simpler is better.

5. **1-aligner fallback in 5+ agents is devastating**: TV350's `min_res < 10 → 1 aligner`
   drops to 1 aligner for 5+ agents, stranding 5+ miners. The aligner floor (TV469)
   and lower thresholds (TV473) both address this.

## Match Analysis

| Variant | Avg | 6v2 | 4v4 | 2v6 | Matches |
|---------|-----|-----|-----|-----|---------|
| v866 (TV473) | 8.71 | 11.20 | 10.38 | 6.09 | 16 |
| v869 (TV474) | 5.58 | 9.25 | 5.91 | 3.25 | 12 |
| v858 (TV469) | ~6.3 | mixed | mixed | mixed | 12 |

## Opponent Insights

- **modular-lstm**: 4v4 scores vary wildly (0.99 to 11.42). Map RNG is a major factor.
- **slanky**: Surprisingly beatable even in 2v6 (10.88, 12.98). Possibly weak alignment strategy.
- **Paz-Bot**: Consistently mid-high scores (10-15). Good benchmarking opponent.
- **coglet-v0**: Variable (1.50-6.81 in 6v2). Unpredictable.
- **mammet**: 2v6 is hardest (0.48-1.13). Strong 6-agent play.

## Strategic Insights

- Lower budget thresholds help across all matchup types (faster ramp to more aligners)
- Don't combine multiple fixes — each additional modification introduces friction
- The heuristic ceiling may be higher than 15.05 with correct threshold tuning
- Parallel session's TV471 hub-recovery scored 11.42 vs modular-lstm (promising direction)
