# Session Learnings: 2026-03-28-121219

## Key Discoveries

### 1. Idle-Mine vs Idle-Explore
- When aligners have no frontier junctions, the original approach was to explore
- **Idle-mine** (have idle aligners mine instead): +89% improvement in self-play (avg 3.18→6.02)
- But in PvP clips mode, idle-mine causes **gear churn**: agents walking through gear stations swap aligner↔miner gear
- **Idle-explore** (just explore to discover junctions): avg 3.97 in PvP clips, best 10.29 — 15% better than idle-mine in PvP
- Self-play performance doesn't predict PvP/tournament performance

### 2. Hotspot Flip (Re-Alignment Boost) Bug
- AlphaCogAgentPolicy had `_hotspot_weight=8.0` but didn't override `_junction_hotspot_count`
- This meant hotspot PENALIZED re-alignment instead of boosting it
- Fix: return negative hotspot count to create bonus for recently scrambled junctions
- Locally: big improvement. Tournament: unclear — may cause over-prioritization of contested zones

### 3. Gear Churn Problem
- In PvP, agents that idle-mine walk through gear stations near hub
- Gear stations auto-give gear on contact
- Result: aligners accidentally get miner gear, then need to re-acquire aligner gear
- On seed 6: agent 2 lost aligner gear 30 times! Each switch wastes time + resources
- Solution: idle-explore instead of idle-mine avoids gear station paths

### 4. Resource Bottleneck (Germanium)
- On many seeds, one element (often germanium) hits 0
- When any element = 0, hearts can't be crafted → all pressure agents become useless
- The `resource_bias=least` directive helps but isn't enough
- Resource-responsive budget cuts (reducing pressure when resources low) cause death spirals
- Better approach: maintain pressure but let idle aligners mine the scarce resource

### 5. Self-Play ≠ Tournament Performance
- AlphaCyborgPolicy (V4): self-play avg 4.73, PvP clips avg 1.49 (2 wipes)
- AlphaTournamentPolicy (VT3): self-play avg ~3 (lower), PvP clips avg 3.97 (much better)
- The v65-style conservative play (hub proximity, retreat margin 20) performs better against real opponents
- Aggressive 5-6 aligner builds that dominate self-play get punished in PvP

### 6. Wipe Bug
- ~7-25% of seeds, all agents die immediately (HP→0 despite being near hub)
- Hub territory healing not triggering on certain map layouts
- Not fixable in policy — appears to be map/engine issue
- `hub_camp_heal` code still helps (better than not having it)

## Strategy Recommendations
1. Use clips mode (machina_1.clips) for PvP testing, not self-play
2. Conservative play (v65-style) is better for tournament than aggressive play
3. Economy-first: 3 miners minimum, resource-responsive pressure scaling
4. Avoid gear stations with idle aligners — explore instead of mine
5. Scramblers are critical in PvP: 111+ scrambles in high-scoring seeds
