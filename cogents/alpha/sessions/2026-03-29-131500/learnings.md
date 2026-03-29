# Learnings — Session 2026-03-29-131500

## Key Discovery: Hotspot Weight Inversion
- **Default hotspot_weight=8.0** PENALIZES re-aligning scrambled junctions
- Scrambled junctions are already in our network range — re-aligning is CHEAP
- **Negative hotspot weight** makes agents prefer scrambled junctions → faster recovery
- TV28 (hotspot=-10) averaged 8.91 vs TV18's 7.83 in self-play (+13.8%)

## Hotspot Weight Sweep (self-play 10K, 8-agent)
| Weight | Policy | Avg Score | Notes |
|--------|--------|-----------|-------|
| 8.0    | TV18   | 7.83 (n=4)| baseline (avoids scrambled junctions) |
| 0.0    | TV32   | 8.76 (n=1)| neutral — ~baseline |
| -3.0   | TV33   | 8.35 (n=1)| slight preference |
| -5.0   | TV31   | 7.88 (n=2)| high variance (10.18, 5.57) |
| -7.0   | TV34   | 6.00 (n=1)| worse |
| -10.0  | TV28   | 8.91 (n=4)| **BEST** — strong preference |

Note: Self-play has high variance. Single-run results are unreliable.
TV28 is the only variant with enough runs (n=4) for meaningful comparison.

## Failed Improvements
1. **Faster alignment ramp** (TV29): 6.96 — earlier alignment hurts economy
2. **Combined changes** (TV30): 0.00 — total wipeout, agents die immediately
3. **Bolder expansion** (TV35): 7.40 — less conservative margin causes more deaths
4. **Stronger silicon** (TV36): 6.96 in self-play — may differ in tournament
5. **Pure explore stagnation** (TV37): 3.86 — scrambling during stagnation is important!

## Self-play Observations
- Wipeouts (score=0) are map-dependent, affect all policies equally
- Silicon extractors are scarcer (45 vs 50-58 for other resources)
- Late game (step 7000+): economy collapses regardless of policy
- Score accumulates primarily in steps 1000-6000
- Stagnation scramble IS beneficial — removing it costs ~5 points

## Tournament Observations
- All hotspot variants passed qualifying (v392-v401)
- Tournament queue was very slow — no completed matches during session
- Need to check results next session
- New opponents: Paz-Bot-9005, slanky:v112

## What NOT to Change (reinforced)
1. Stagnation timing/offsets (local optimum confirmed again)
2. Budget allocations
3. Stagnation scramble behavior (1/3 scramble is valuable)
4. Early alignment timing (step 200 for 4+ agents is correct)
5. Expansion margin (hp-20 is safer than hp-12)
