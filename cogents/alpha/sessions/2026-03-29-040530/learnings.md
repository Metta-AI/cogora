# Learnings — 2026-03-29-040530

## Breakthrough: TournamentV2 Architecture (v348 = #1 at 7.46)
The winning formula combines THREE elements from different policy families:

### 1. AdaptiveV3 Conservative Budgets (from AlphaBalancedAgentPolicy)
- Scale aligners ONLY when economy permits: 1→2→3→4→5 based on min_resource
- Only allocate 2 aligners until hub has 30+ of each resource
- This prevents the economy crash that kills Aggressive-based policies in tournament
- In tournament, both policies allocate independently — conservative prevents overallocation

### 2. Team-Size Cap (from AdaptiveTeamAgentPolicy)
- Caps aligner+scrambler count to (team_size - 1) to guarantee miners
- In tournament with 4 agents per policy: max 3 non-miners
- Prevents the "all aligners, no miners" death spiral when controlling partial team
- Key: only helps on conservative base; HURTS on aggressive base

### 3. Aggressive Idle Scrambling (from AlphaAggressiveAgentPolicy)
- When no junctions to align: scramble if min_resource >= 14
- This is THE critical differentiator (v348 vs v350: 7.46 vs 2.18)
- Works because tournament opponents are weak — scrambling removes their junctions
- Much better than dedicated scramblers (wastes budget) or no scrambling (wastes time)

## What Doesn't Work in Tournament
1. **Pure Aggressive budgets** (v345: 3.25): Allocates too many aligners, crashes economy
2. **No scrambling** (v350: 2.18): Without denying opponents, they accumulate junctions
3. **AdaptiveTeam + Aggressive base** (v344: 2.48): Aggressive base + cap = too few aligners
4. **Crisis mode economy** (V2a: 5.58 local): Cutting aligners when min_res=0 kills score average

## Tournament Environment Insights
- v290 (old #1 at 6.50) played under different rules; environment changed
- Fresh uploads of same policy score ~3 instead of 6.5
- Tournament uses 4-agent matches primarily (2 per policy)
- Match pairing: your policy + partner policy vs Clips AI
- Both policies contribute to shared hub economy
- Score = average friendly junctions per step over 10k steps

## Economy Collapse Pattern (Local 8a)
- Steps 0-1000: Ramp to ~22 junctions (economy 100-300 each)
- Steps 1000-2500: Peak at 20-22 junctions
- Steps 2500-5000: Decline to 10-12 (carbon depletion)
- Steps 5000-10000: Collapse to 4-8 (economy dead)
- Carbon is 3x bottleneck (aligner gear costs 3 carbon)
- Silicon is secondary bottleneck

## Seed Variance
- Local 8a scores range 5-11 depending on seed
- Tournament averages over ~72+ matches smooth this out
- seed 1: 10.62, seed 42: 6.77, seed 7: 5.12 for AdaptiveTeam

## AdaptiveV4 (Faster Ramp) = 5.75 in Tournament
- Lowering resource thresholds by 20% improves score
- But still much below v348's 7.46
- The combination of cap + scramble + conservative base is unique to v348
