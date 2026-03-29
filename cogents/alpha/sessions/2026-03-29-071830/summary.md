# Session 2026-03-29-071830 Summary

## Key Achievements
1. **Discovered scout agent architecture** — dedicating 1 agent to permanent exploration
   discovers far more junctions (14→~40+ out of 65), leading to +28% at 5K and +253% at 10K
2. **Self-play >10 goal achieved** — ScoutExplore avg 10.85 at 10K steps (seeds 0-3)
3. **Tournament reality check** — ScoutExplore hurts at 2-4 agents (avg 5.19 vs v348's 7.5)
4. **AdaptiveScout (v362)** — only scouts at 6+ agents, protecting small teams

## Tournament Results
- v359 (ScoutExplore): avg ~5.19 — worse than v348 due to scout overhead at small teams
- v360 (TwoScouts): 2.31 at 4a, 5.62 at 2a — too many scouts
- v362 (AdaptiveScout 6+): results pending, expected to match v348 at 2-4a + beat at 6a

## Key Insight
Self-play ≠ tournament. Scout excels when BOTH teams use it (self-play), but hurts
in tournament where only one team has the scout overhead and agent counts vary.
The >10 goal may require the AdaptiveScout approach (scout only at 6+ agents)
or fundamentally different strategies.

## Uploads: v359, v360, v361, v362
