# Learnings — 2026-03-30-061317

## Key Discovery: Team-Size-Specific Stagnation Thresholds

The single biggest improvement this session: using different stagnation detection
parameters based on team size.

| Team Size | Peak Threshold | Steps No Growth | Min Step | Rationale |
|:---------:|:--------------:|:---------------:|:--------:|-----------|
| 2a | 3 | 200 | 300 | Fast stag entry — proven +1.45 pts vs TV142 |
| 4a+ | 5 | 300 | 500 | Conservative TV142 — proven optimal |

Combined with TV162's lower 6a thresholds (25/40/80 vs 30/50/100), this created
**TV186 (v542) = #2 at 14.39** — essentially tied with #1 (v522=14.41).

## Per-Team-Size Analysis

| Version | TV | 2a | 4a | 6a | Overall | Rank |
|---------|------|------|------|------|---------|------|
| v522 | TV162 | 12.75 | 13.24 | **15.75** | **14.41** | #1 |
| **v542** | **TV186** | **14.20** | 12.90 | 15.50 | **14.39** | **#2** |
| v519 | TV160 | 13.73 | 13.20 | 15.37 | 14.37 | #3 |
| v543 | TV187 | 13.60 | 13.30 | 15.20 | 14.31 | #6 |
| v544 | TV188 | 12.60 | **13.40** | 15.30 | 14.26 | #7 |
| v545 | TV189 | 14.00 | 13.10 | 14.70 | 14.05 | #10 |

## Cooperative Scoring Dynamics

- Both teams always get identical scores
- Score = shared metric (total aligned junctions per tick across both teams)
- 2a score heavily dependent on opponent's 6a quality (can't control)
- 50% idle scramble proven optimal (junction recycling creates alignment opportunities)
- Scrambling during stagnation prevents game from stalling

## Match Log Insights

Analyzed 6a vs gtlm and 4a vs slanky matches in detail:
1. Agents peak at ~11-18 junctions around step 500-1000
2. Stagnation triggers, agents switch to scramble mode
3. By step 2000, junction count collapses to 2-5
4. By step 10000, junction count at 0-2
5. Opponent often has 20+ junctions

This collapse is fundamental to the game dynamics. The stagnation scramble is
actually the SOLUTION (creates junction turnover), not the problem.

## What Didn't Work

1. **Network-aware scramble targeting** (TV179-TV184): -3-4 pts. Distance > targeting intelligence.
2. **Wider exploration in stagnation** (TV190/v546): qualified at 10.43 — too slow.
3. **Reduced scramble** (TV189/v545): 14.05 — slightly worse than 50% scramble.
4. **TV185 faster early ramp**: v541 converged to 13.02 — didn't help.

## What Worked

1. **Team-size stagnation** (TV186/v542): 14.39 = #2! Best new finding.
2. **Faster 4a expansion** (TV188/v544): 14.26 = #7, 4a=13.4 (best 4a).
3. **Combined stagnation + 2a mining** (TV187/v543): 14.31 = #6, very balanced.

## Still Pending

- **v547 (TV191)**: TV186 + faster 4a (min_res 15). Still qualifying.
  If it combines v542's 2a=14.2 with v544's 4a=13.4, it could reach ~14.5 = new #1.
- **v546 (TV190)**: wider exploration. 63 running matches.
