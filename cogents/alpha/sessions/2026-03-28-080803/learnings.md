# Learnings — Session 2026-03-28-080803

## Key Findings

### 1. Re-alignment Boost is a Major Win
- Flipping the hotspot penalty to a bonus (prioritizing recently scrambled junctions for re-alignment) is the single most impactful improvement
- RealignBoost (avg 3.84) vs V65True (avg 3.37) = +14% from hotspot flip alone
- Previously, the hotspot_weight bug nullified this effect (was 0.0 in V65Replica inheritance)

### 2. Budget Stability Matters More Than Budget Levels
- StableBoost (avg 4.20) vs RealignBoost (avg 3.63) = +16% from role stability
- The key change: tighter economy threshold (drop budget at min_res < 2, not < 3)
- Agent 4 switching roles 10 times on low-scoring seeds wasted massive resources on gear churn
- Floor of 3 (not 2) when economy is critical prevents total collapse

### 3. Scramblers Are Critical (Even in Self-Play)
- Removing scramblers consistently hurts: NoScramble avg 1.42, V65NoScrambleBoost avg 1.25
- Scramblers free up enemy junctions for our aligners — indirect but vital
- Even 1 scrambler makes a huge difference

### 4. Standard Targeting Beats V65 Hub-Penalty
- Base aligner_target_score with expansion_weight=10, expansion_cap=60 outperforms v65 scoring
- V65 scoring caps expansion at 30 — too conservative for network growth
- Network_weight=0.2 (mild proximity preference) works with standard scoring

### 5. Zone-Based Targeting: High-Variance Bet
- Zone targeting (N/E/S/W sector preference per aligner) achieved 10.63 on seed 5
- But also crashed seed 1 from 4.90 to 1.74
- Overall avg nearly identical (4.22 vs 4.20)
- Zone bonus is map-dependent — works when junctions are spread, fails when clustered

### 6. Seed/Map Variance Dominates
- Score range: 0.00 to 10.63 across seeds
- ~7% of seeds cause total wipe (all agents die immediately)
- Score is primarily determined by junction layout relative to hub
- Early alignment matters most — junctions aligned in first 1000 steps contribute most to average

### 7. Economy Math
- Hub starts with num_agents*3 of each element
- 2-agent mode: only 6 of each — can't even afford 1 heart initially
- 8-agent mode: 24 of each — comfortable for 4+ aligner gears
- Heart cost: 7 of each element
- Alignment cycle: ~98 steps per alignment (vs theoretical ~31) — 3x overhead from economy waits, travel, retreats

## Strategy Rankings (15-seed averages, 5k steps)
1. ZoneBoost: 4.22 (max 10.63, high variance)
2. StableBoost: 4.20 (max 9.23, more consistent)
3. RealignBoost: 3.63 (baseline for improvements)
4. V65True: 3.37 (best simple policy)
5. AlphaCyborg: 2.04 (original)
