# Learnings — 2026-03-30-221202

## Zero-Scrambler is NOT a Bug
- TV334+ (including v716/TV350) all return scrambler_budget=0 in `_pressure_budgets`
- The base semantic_cog has scrambler logic (1 at step 100, 2 at step 3000), but TV334+ overrides it
- v716 achieved 15.05 WITH zero scramblers — this is the intended design
- Adding dedicated scramblers (TV455-TV461) hurts by reducing aligner count
- Score = avg aligned junctions per tick. Scramblers reduce enemy score, NOT increase ours.
- Exception: aligners DO scramble opportunistically when idle (non-stagnation path)

## TV350 Base is Sacred — Don't Touch It for 5+ Agents
- v847 (TV462, TV350 for 5+): 13.59 vs Paz-Bot 6v2 — closest to v716's 15.05
- v853 (TV466, aggressive stag scramble): avg ~4.76 — stag changes hurt
- v851 (TV465, floor+crisis): 6v2 lstm=7.87, 4v4 Paz=11.32 — decent but not v716
- Pattern from all sessions: any modification to TV350's 5+ agent logic regresses
- TV350's simplicity IS its strength: max aligners, let them scramble when idle

## Floor 3 Still Hurts in 6v2
- Floor forces 3 aligners in crisis (min_res < 10), leaving only 1-2 miners
- Not enough miners = slow resource recovery = prolonged crisis
- TV350 drops to 1 aligner in crisis, freeing 5-6 miners for fast recovery
- The "death spiral" is actually SHORTER with no floor (faster mining recovery)

## 2-Agent Matchups Remain the Weakness
- 2v6 scores range: 0.18 (v840 vs gtlm) to 11.91 (v840 vs Paz-Bot)
- TV465 (2-agent fix, always 2 aligners): 2.89-4.40 vs mammet 2v6 — better than 0.18
- Fundamental issue: heuristic policy can't match RL-trained 2-agent play
- modular-lstm with 2 agents controls 8+ junctions vs our 6 agents' 2

## Self-Play is Unreliable
- Self-play (same policy both sides) gives very different scores than competition
- TV452 baseline: 2.68/cog self-play, but variants of it scored 8-16 in competition
- TV466: 0.69/cog self-play but decent in competition (6.80 4v4 vs gtlm)
- NEVER optimize for self-play. Always test in tournament.

## Competition Result Summary
- v847 (TV462): 13.59 vs Paz 6v2 — BEST of new variants (preserves TV350 for 5+)
- v851 (TV465): avg ~6.98 across 5 matches
- v852: avg ~9.98 across 4 external matches
- v853 (TV466): avg ~4.76 across 4 external matches (stag scramble hurts)
- v854 (TV466): 9.41 vs random 6v2
- None beat v716's 15.05 consistently

## Version Map (this session)
v842=TV455, v844=TV460, v845=TV461, v846=TV350, v847=TV462, v848=TV463
v853=TV466/v854=TV466 (uploaded twice)
(From concurrent 212420): v849=?, v850=TV464, v851=TV465, v852=?

## Next Steps
1. Re-upload pure TV350 and get MORE competition data — v716's 15.05 may be a high-variance result
2. Focus 2-agent improvements ONLY (don't touch 5+ budget)
3. Consider pre-game LLM strategy (not per-step) to break heuristic ceiling
4. Study modular-lstm's 2-agent efficiency in detail
