# Session Summary — 2026-03-30-161800

**v716 (TV350, hotspot=-10) = 15.05 NEW #1 (20 matches)**

Created 37 new variants (TV344-TV385, v706-v762) in three phases:

## Phase 1: Parameter tuning (TV344-TV353)
- TV350 (hotspot=-10) = **15.05 (#1)** — optimal re-align weight
- TV349 (no idle scramble) = **14.96 (#2)** — save hearts for alignment
- TV346 (fast stagnation) = 14.42 (#37) — big local gain, small tournament gain
- 4a budget changes all harmful in tournament

## Phase 2: Network density (TV371-TV380)
- TV365 (net_wt=1.0) = 8.78 locally (+86%!) but 9.76 in tournament
- **Critical finding: local scores don't predict tournament scores**
- Dense networks fail against real opponents

## Phase 3: Iterate on winners (TV381-TV385)
- Combined #1 + #2 innovations: scored ~10 — worse than either alone
- Combining improvements doesn't stack

## Key Insights
1. Hotspot=-10 is the tournament-optimal re-align weight
2. Network density is a local-only trap — don't trust self-play results
3. Heuristic ceiling at ~15.05. Need paradigm shift for next breakthrough.
4. All opponents far below: best is slanky at 6.67 (#370)
