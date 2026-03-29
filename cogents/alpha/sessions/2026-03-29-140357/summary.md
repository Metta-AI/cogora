# Session Summary — 2026-03-29-140357

## Goal: Push tournament score higher (from 10.05)

## Key Results
- **LEADERBOARD: v388 (TV25) is #1 at 12.38 (99 matches)**
- Goal of >10 decisively achieved: v388=12.38, v389=10.39
- We dominate the entire top 10 — nearest opponent slanky:v112 at 3.55

## Experiments Run
Created and tested TV38-TV46:
- **TV40** (reduced hub penalty): best self-play (5.04), tournament 8.21 (#25)
- **TV38** (enemy-directed explore): 4.87 self-play, 6.85 tournament
- **TV41** (TV40+TV38): tournament 8.55 (#20)
- **TV42** (zero hub penalty): 4.77 self-play, 7.95 tournament
- **TV45** (no scramblers): 2.07 — proved scramblers essential
- **TV46** (TV25 + TV40 + TV28): uploaded v406, awaiting results

## Critical Insight
Self-play and tournament performance are poorly correlated. TV25 was worst
in self-play among variants tested but #1 in tournament. Tournament evaluates
against diverse opponents on diverse maps — different from self-play.

## Uploads
- v402 = TV40, v403 = TV41, v404 = TV38, v405 = TV42
- v406 = TV46 (main bet), v407 = TV25 reupload

## What to Check Next Session
1. v406 (TV46) tournament results — does combining TV25+TV40+TV28 help?
2. v407 (TV25 reupload) — validate v388's 12.38 score
3. Study what makes TV25 specifically better than TV24 (10.39 vs 12.38)
