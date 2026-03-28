# Session 2026-03-28-181220 Learnings

## Key Discovery: Miner Sticky Target Bug
The biggest discovery this session: miners get locked to wrong resources
via sticky targets. When `_TARGET_SWITCH_THRESHOLD=3` and a miner is
sitting on a silicon extractor (distance 0), it won't switch to a
carbon extractor 10+ tiles away even when carbon = 0 in the hub.

**Fix**: Clear sticky target when:
1. Least resource < 7 and miner is mining a different resource
2. Miner is mining the most abundant resource (>80% of max) while
   least resource is < 50% of max (ratio-based rebalancing)
3. Resource bias changed and least resource is < 14

## Tournament Insights
- **Team-relative roles ESSENTIAL**: v258 (global) scored 1.59 while
  v259 (team-relative) scored 2.47. Tournament uses 2+6/4+4/6+2 splits.
- **v259 at 2.47** (39 matches) — resource fix helps but doesn't
  break the ceiling (v65 still #1 at 3.59)
- **Hotspot weight hurts tournament**: Confirmed by prior sessions,
  set to 0 in latest uploads (v268-v269)

## Self-Play Results
- **10k scrimmage (EconFix)**: avg 5.49, peak **9.48** (nearly target!)
- **5k scrimmage**: EconFixGlobal 4.38 vs AlphaCyborg 4.25 (modest +3%)
- **Carbon bottleneck fixed**: hub carbon at step 1000 went from 0 to 1025

## Late-Game Economy Collapse
- At 10k steps, clips overwhelm after step 5000
- Silicon depletes first (only 45 extractors vs 50-58 for others)
- By step 7000: silicon=0, economy collapses, territory lost
- AlphaLateGamePolicy adds phase-based budgets (more scramblers after 5000)

## What Didn't Work
- RL training on CPU: 0 SPS, completely impractical
- Global role assignment in tournament (despite better self-play scores)
- More complex targeting (hotspot/network weights) hurt in tournament

## Architecture Notes
- The gap from 3.59 (v65) to >10 (target) requires fundamentally different approach
- Heuristic ceiling confirmed at ~3-4 in tournament
- RL with GPU is likely the only path to >10
- LLM enhancement marginal (+0.1) based on prior sessions

## Versions Uploaded
- v258: EconFixGlobal (1.59 — global roles hurt)
- v259: EconFix team-relative (2.47 — best new version)
- v260: EconFixGlobal v2 with ratio fix (1.64)
- v261: V65PlusFix with global roles (1.67)
- v264: AlphaLateGame team-relative (2.35)
- v265: EconFix refresh (1.97)
- v266: LLM AnthropicCyborg (pending)
- v267: V65 true replica team-relative (pending)
- v268: EconFix no hotspot (pending)
- v269: LateGame no hotspot (pending)
