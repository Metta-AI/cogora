# Session 2026-03-28-231500 — Summary

## Key Achievement
Created AlphaChainExpandPolicy (+132% local 8a) and uploaded 8 tournament versions.
Discovered that economy-gated budgets + chain expansion weights (expansion_weight=20)
synergize for massive local improvement.

## Tournament Status
- #1: v290 (Aggressive economy fix) at 6.54 — still king
- #3: v309 (AdaptiveV3) at 5.56
- #4: v311 (ChainExpand) at 5.52
- v312 (ChainDefense) at 3.06 — defense hurts vs weak opponents
- v313-v316 qualifying (fresh builds with all fixes)

## Critical Learning
Tournament and local scores diverge: aggressive play beats conservative play
in tournament because opponents are weak. Defense/economy management helps
vs strong opponents (clips AI) but hurts vs weak ones.

## Policies Created
- AlphaBalancedPolicy: Economy-first, silicon mining
- AlphaAdaptiveV3Policy: Dynamic aligner scaling
- AlphaChainExpandPolicy: expansion_weight=20, explore idle
- AlphaChainDefensePolicy: + late-game defense
- AlphaMaxChainPolicy: expansion_weight=30 (FAILED)
- AlphaAggroChainPolicy: Aggressive + chain weights + silicon

## Next Steps
- Monitor v313-v316 tournament results
- Score > 10 likely needs RL training or LLM cyborg
- Heuristic tournament ceiling appears to be ~6.5
