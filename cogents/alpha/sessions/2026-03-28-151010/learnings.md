# Session 2026-03-28-151010 Learnings

## Key Findings

### 1. idle-mine >> idle-explore for AlphaCyborg
- CyborgV2 (idle-explore) 10k clips avg: 3.54
- Original Cyborg (idle-mine) 10k clips avg: **8.05**
- idle-mine keeps economy running when aligners have no frontier junctions
- The VT3 idle-explore improvement was specific to AlphaTournament, NOT AlphaCyborg
- AlphaCyborg's expand-toward and hotspot features depend on mining economy

### 2. Old deps (cogames 0.19) provide marginal tournament advantage
- v241 (V65TrueReplica + old 0.19): settling ~2.35 (#62-72)
- v231 (AlphaCyborg + current 0.21): 2.11 (#150)
- Advantage: +0.2-0.3, not the dramatic 2x initially suggested
- Old deps make clips mode MUCH harder locally (avg 0.55 vs 3.87)
- PvP tournament dynamics differ from clips NPC dynamics

### 3. Game reproducibility confirmed
- Same seed + policy → consistent results (±3 variance, not ±15)
- Seed 5 consistently scores 15-20 on 10k clips (28-33 junctions held)
- High score variance is from seed differences, not randomness

### 4. Tournament ceiling is structural
- Well-converged old versions (v17/v11/v38, 900+ matches): 2.75-2.81
- All new versions (20-30 matches): settling at 2.1-2.4
- v65 at 3.59 is an outlier (different era/opponent pool)
- Score >10 not achievable with current game mechanics + PvP format

### 5. Radical strategies all failed locally
- FlashRush (all-mine first): avg 1.72 (vs baseline 3.18)
- EconDominance (5 miners): 0.00 (wipe)
- ScrambleDominance (4 scramblers): 1.67 clips, 2.12 self-play
- Early economy mining doesn't help — territory grab speed matters more

### 6. AlphaTournament > AlphaCyborg in tournament (but not locally)
- AlphaCyborg: 3.87 clips avg, 2.11 tournament
- AlphaTournament: 3.18 clips avg, 2.08 tournament (initially)
- Conservative play (retreat 20, economy-first budgets) helps PvP survival

### 7. Tournament uses variable team sizes (6v2, 2v6, 4v4)
- 2-agent games are hard losses (VT: 0.00 wipe, Cyborg: 0.19)
- 6-agent team has massive advantage
- Overall score averages across favorable and unfavorable splits
