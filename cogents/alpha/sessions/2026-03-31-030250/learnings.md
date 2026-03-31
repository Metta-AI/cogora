# Learnings — 2026-03-31-030250

## TV488 (v884) = Best Variant at avg 9.58
- **4v4 aligner floor** (never below 2) was the key improvement over TV478 (v873)
- Combined with 5+ aligner floor from TV484
- No desperate mode, no stagnation changes from TV478

## Budget Changes Are Dangerous
Every budget modification from TV488 regressed:
- **TV489 (v885)**: Aggressive stagnation scramble → avg 5.90 (REGRESSION)
  - Always-scramble wastes hearts. step%200 time window is IMPORTANT.
  - min_res >= 7 threshold prevents scramble when economy is failing.
- **TV490 (v888)**: Faster 3-aligner ramp → avg 6.91 (REGRESSION)
  - 4v4: 2→3 aligners at min_res 30 (was 60) starves economy.
  - 5+ agents: 3 aligners at min_res 22 (was 35) same problem.
- **TV491 (v887)**: Scorched earth → avg ~4.63 (REGRESSION)
- **TV492 (v889)**: 4v4 scrambler → avg ~8.33 (REGRESSION)

## Resource Imbalance Is Map-Dependent
- In bad matches, one resource (usually germanium or silicon) hits 0 while others accumulate to 500+
- Miners mine whatever's nearby; if extractors for the scarce resource aren't nearby, imbalance grows
- Hub can't make hearts when any resource is below 7
- This creates a death spiral: no hearts → mine instead of align → lose territory → can't recover

## Opponent Insights
- **coglet-v0**: Effective scrambler. Beat us 6v2 (2.03) by scrambling faster than we realign.
- **mammet**: Strong 4v4. Beat us 3.95. Economy management may be superior.
- **slanky**: Variable performance. 2v6 scores range 6-14 (high variance).
- **modular-lstm**: Tough 2v6 opponent (score 1.83).

## Heuristic Ceiling Is Real
- ~10 appears to be the ceiling for pure heuristic approaches
- Budget tuning produces diminishing returns or regressions
- Next step should be RL training or LLM-based adaptation
