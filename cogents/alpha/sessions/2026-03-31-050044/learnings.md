# Learnings — 2026-03-31-050044

## CRITICAL: Tournament Runs 10000 Steps, Not 5000
- Local tests were using 3000 steps. Tournament matches run 10000 steps.
- Late-game (step 5000+) resource depletion is a major issue not visible in short tests.
- Always test with `--steps=10000` for accurate tournament simulation.

## CRITICAL: Qualifying Score ≠ Competition Score
- Previous sessions reported "avg 9.58" for v884 — this was the QUALIFYING average.
- Competition scores are much lower (0.18-3.95 range for v903).
- The "score > 10" goal likely refers to qualifying score, not competition.

## Economy Crash Is the #1 Problem in Tournament
- v903 competition avg: 1.33 across 18 matches.
- Worst match (0.18 vs modular-lstm 4v4): total economy collapse.
  Hub resources < 10 from step 500. 0 aligned junctions from step 2000.
- Root cause: `policy_env_info.num_agents` = 8 (total agents in game).
  With 5+ path giving 5 pressure, a 4-agent team has 0 dedicated miners.
- Fix: cap pressure to `max(team_size - 2, 2)` using `len(shared_team_ids)`.

## Shared Extractor Claims Help Miner Efficiency
- Multiple miners converge on same extractor → inefficient.
- Shared extractor claims (like junction claims) spread miners to different extractors.
- Local test improvement: avg 2.10 vs 1.95 baseline (+8%).

## Hotspot Patrol Improves Territory Retention
- When idle aligners mine instead of patrolling, territory declines 23→7 over 5000 steps.
- Hotspot patrol: move toward recently-scrambled junctions to be positioned for re-alignment.
- BUT must gate on economy health (min_res >= 14) to avoid starving mining.
- Ungated patrol: avg 2.55 in local. Gated: avg 2.41. Both better than baseline 1.95.
- Territory at step 2500: 19 friendly (patrol) vs 10 (baseline).

## Aggressive Mining Stall Detection
- When bottleneck resource is at 0: reduce stall threshold to 20 steps (was 50).
- When resource < 3: threshold = 30. Otherwise: 50.
- This prevents miners from sitting at depleted extractors too long.
- v910 10k score: 3.25 (vs 2.85 without).

## Silicon Death Spiral Is Structural
- Silicon extractors (45) are fewest on the map.
- When silicon hits 0: can't make gear, can't make hearts → everything stalls.
- Carbon/germanium accumulate to 500+ while silicon stays at 0.
- Late-game (step 5000+) resource depletion is unavoidable on some maps.
- No heuristic fix — need RL or smarter extractor discovery.

## Early Heart Skip Didn't Help
- Tested: skip heart batching for first 300 steps (go align with 1 heart).
- Gets first junctions aligned faster (4 junctions by step 300 vs 2).
- But overall score: avg 2.03 vs 2.10 without (slightly worse).
- Per-trip efficiency matters: 1 heart per trip = more hub travel time.

## Versions Uploaded This Session
- v904: extractor claims only
- v905: extractor claims + early heart skip (REVERTED heart skip)
- v906: + ungated hotspot patrol (ECONOMY CRASH in tournament: 0.34)
- v907: + economy-gated patrol + miner floor (team_size-1)
- v908: reverted heart skip + economy-gated patrol + miner floor (team_size-1)
- v909: stronger miner floor (team_size-2 = 2 dedicated miners)
- v910: + aggressive mining stall detection (20/30/50 thresholds)

## Best Local Results
- 3000 steps: avg 2.55 (claims + ungated patrol), avg 2.41 (claims + gated patrol + floor)
- 10000 steps: 3.25 (v910, all improvements)
- Baseline (no changes): 1.95 (3000 steps)

## Tournament Results This Session
- v905: 1.63 (2v6 vs Paz-Bot)
- v906: 0.34 (4v4 vs random-assay) — economy crash, no miner floor
- v907: 0.39 (2v6 vs gtlm-reactive)
- v908, v909, v910: in competition, no results yet
