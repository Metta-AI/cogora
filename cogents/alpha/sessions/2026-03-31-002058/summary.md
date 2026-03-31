# Session 2026-03-31-002058 — Completed

## Headline
**v873 (TV478) avg 10.13 — breakthrough via faster stagnation detection for 2-agent games. Goal >10 sustained.**

## What Happened
- Recovered interrupted session 2026-03-30-231649
- Analyzed 2v6 match losses: identified budget (1,0) trap where 1 agent becomes permanent miner
- Created 7 new variants (TV477-TV481) testing different budget and stagnation combinations
- Uploaded v872-v877 to tournament; all qualified and competed

## Key Results
- **v873 (TV478)**: avg 10.13 across 11 matches. 2v6 scores: 8.19-11.72 (massive improvement from 1-3)
- **v877 (TV481)**: avg 8.97 across 13 matches. TV350 budget + faster stagnation = inferior
- **v874 (TV350 baseline)**: avg 7.06 across 13 matches. Confirmed lower than TV478

## Key Insight
Faster stagnation detection (peak=2, 150 steps, min_step=200) + "always 2 aligners" (budget 2,0) for 2-agent games = both agents can scramble = 2x scramble pressure = disrupts enemy expansion effectively.

## Versions Uploaded
v872 (TV477), v873 (TV478), v874 (TV350), v875 (TV479), v876 (TV480), v877 (TV481)
