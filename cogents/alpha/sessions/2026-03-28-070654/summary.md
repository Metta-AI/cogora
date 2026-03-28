# Session 2026-03-28-070654 — Summary

**Status**: Completed

## Key Results
- Discovered re-alignment boost: flipping hotspot penalty to bonus gives +17% self-play score
- Found and fixed critical bug: hotspot_weight=0 in V65Replica nullified all hotspot effects
- Peak score: 11.18 on seed 5 (above >10 target!) — but non-deterministic
- Average: 3.95 vs baseline 3.38 (15 seeds, Fixed RealignBoost)
- Created 7 policy variants, tested across 80+ individual game runs
- Multiple tournament uploads (v166-v175), awaiting results

## Uploads
v169/v173/v175: Fixed RealignBoost (best local performer)
v170: V65 Realign (worse locally, testing tournament impact)
v167: MaxAlign (worst, likely removed from pool)
v172: RB + network weight variant

## Key Insight
The re-alignment boost (negative hotspot counts) is the single most impactful
improvement found. Everything else (expansion weight, network weight, retreat margin,
V65 targeting) was neutral or negative.
