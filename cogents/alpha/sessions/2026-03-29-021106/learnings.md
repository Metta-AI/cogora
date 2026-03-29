# Learnings — 2026-03-29-021106

## Architecture Insight: num_agents Bug is Actually a Feature
- `policy_env_info.num_agents` returns TOTAL agents (8 in 4v4), not per-team (4)
- For 4v4 (75% of tournament), this "bug" gives MORE aligners → higher scores
- TeamFix (correct team size) is TOO CONSERVATIVE for 4v4 — fewer aligners
- **Don't fix the num_agents bug for 4v4 policies**

## Carbon Bottleneck
- Carbon is consumed 3x by aligner gear (carbon:3, oxygen:1, germanium:1, silicon:1)
- Hub carbon hits 0 by step 6000 in most games
- Aligners spend 70% of time (steps 3000-10000) emergency mining instead of aligning
- **Carbon-biased mining** is the #1 improvement: AllCarbon avg 8.13 vs Aggressive avg 3.15 on 8a

## Resource Priority System
- `resource_priority()` sorts by (inventory_amount, bias_flag, name)
- When carbon=0, ALL miners target carbon regardless of bias
- But having carbon as default bias means miners START on carbon extractors
- This avoids the critical death spiral on bad seeds where no miner finds carbon

## Death Spiral Mechanics
- On some seeds, Aggressive agents die within 100 steps and never recover
- Root cause: early mining decisions leave no carbon for hearts/gear
- Carbon bias prevents this by ensuring early mining prioritizes carbon
- The death spiral is why Aggressive avg drops to 3.15 (one 0.00 seed destroys the avg)

## Scrambling is Essential
- Removing scramblers (Coop, HighEff) → score drops to 0-1.38
- Even with "cooperative scoring", Clips ships scramble our junctions
- Scramblers protect our network; without them, Clips destroys all aligned junctions
- Keep 1-2 scramblers in all tournament policies

## Mining Efficiency
- Higher deposit threshold (20) HURTS — resources don't reach hub fast enough
- Current threshold (12) is well-tuned
- Reducing (8) doesn't help either
- Economy-gated budgets (SustainV2) are too conservative — too many miners, not enough aligners

## Test Format Confusion
- `-c 8` = 4v4 (4 per team, 8 total) = MAIN tournament format (75%)
- `-c 4` = 2v2 (2 per team, 4 total) = MINORITY format (25%)
- Early in session, mistakenly optimized for 4a (2v2) instead of 8a (4v4)

## Junction Trajectory Pattern
- Steps 0-500: Ramp to 16j
- Steps 500-2500: Peak 17-20j
- Steps 2500-5000: Decline to 7j (carbon depletion + Clips scrambling)
- Steps 5000-10000: Flat at 7j (economy dead)
- Score killer: 5000 steps at 7j instead of 15j = ~4 points lost

## Variance
- Single-seed results are UNRELIABLE (range: 0.00 to 9.35 for same policy)
- Need 3+ seeds for valid comparison
- Tournament averages over many matches — consistent policies win
