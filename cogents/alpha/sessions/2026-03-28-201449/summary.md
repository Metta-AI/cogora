# Session 2026-03-28-201449 Summary

Found and fixed miner sticky-target bug in AlphaCogAgentPolicy (+86% self-play).
Tried shared WorldModel (broke pathfinding — reverted). Tested AlphaHybrid
(v65 targeting), AlphaSoftHub, AlphaNoScramble variants. All heuristic versions
converge to 2.0-2.5 in tournament. Uploaded v270-v279 (v275/v276 broken).
Tournament ceiling is structural — RL with GPU needed for >10.
