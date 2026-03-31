# Learnings — 2026-03-31-062303

## CRITICAL: Competition vs Local Resource Scales Are Fundamentally Different
- Local play: hub resources accumulate to 1000+ (abundant)
- Competition play: hub resources max ~50 (scarce, always constrained)
- All thresholds calibrated for local play (min_res >= 14) NEVER fire in competition
- This was the root cause of many budget features being inert in tournament

## CRITICAL: Tournament Policy Missing Key Improvements
- AnthropicPilotAgentPolicy (used in tournament) inherits from PilotAgentPolicy,
  NOT from AlphaCogAgentPolicy
- Missing features: extractor claims, hotspot patrol, expansion toward unreachable
  junctions, lower retreat margins, team-size miner cap
- All improvements were only in the local-play class (AlphaCogAgentPolicy)

## Fix: Lower Resource Thresholds for Competition
- 2nd scrambler gate: min_res >= 5 (was 14) — now actually fires in competition
- 1st scrambler gate: min_res >= 5 (was 7) — fires more reliably
- Patrol threshold: min_res >= 3 (was 14) — allows defensive positioning in scarcity
- Result: v912 competition avg 1.93 (vs v909/v910 avg ~1.33) — 45% improvement

## Fix: Team-Size Miner Cap Prevents Economy Crashes
- `policy_env_info.num_agents` = 8 (total) regardless of team size
- Without cap, a 4-agent team with pressure_budget=5 has -1 miners (impossible)
- Added: `pressure_budget = min(pressure_budget, max(team_size - 2, 2))`
- Ensures at least 2 miners on every team size

## Fix: Improved Aligner Action for Tournament
- Base SemanticCog aligner: just explores when no targets (wanders aimlessly)
- Added to tournament policy: expansion toward unreachable junctions,
  hotspot patrol (positions near recently-scrambled areas), idle-mine fallback
- Also added lower retreat margins (15 instead of 20) for more productive time

## Self-Play Testing Has HIGH Variance
- Map RNG causes wipeouts (score 0.00) or good runs (6.93) on same policy
- 3-run averages at 5k steps: Baseline 3.36, V3 3.16 (within variance)
- Self-play changes are hard to validate: scramblers useless when both teams mirror
- Competition is the only reliable signal

## Competition Results Summary
- v912 (AlphaCyborgV2): 15 matches, avg 1.93
  - Best: 5.32 (4v4 vs slanky) — 5x improvement from v910's 1.06
  - 6v2 vs random-assay: 4.34 (was 1.30) — 3.3x improvement
  - 2v6 matches still very hard (0.25-0.28)
- v909/v910: 18 matches, avg ~1.33

## Mining Stall Detection Helps
- Aggressive thresholds (20/30/50 steps) added to tournament policy
- When bottleneck resource at 0: after 20 stall steps, force explore for new extractors
- Prevents miners from sitting at depleted extractors

## Versions Uploaded This Session
- v911: AnthropicCyborgPolicy with competition fixes (team cap, lower thresholds)
- v912: AlphaCyborgV2Policy (heuristic-only, competition thresholds)
- v913: AnthropicCyborgPolicy + improved aligner action + retreat margins
