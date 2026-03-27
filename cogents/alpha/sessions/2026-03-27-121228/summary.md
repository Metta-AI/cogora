# Session Summary: 2026-03-27-121228 (Interrupted)

## Key Achievements
- Discovered clips ships are STATIONARY, auto-scramble within 15 cells every 70 ticks
- Implemented scramble-zone inference to avoid dangerous junctions
- BREAKTHROUGH: v8 scored 4.92 in 10k test (3x improvement from ~1.5)
- Tournament: v30 is #1 on leaderboard at 1.92, holding top 5 spots
- Uploaded v37 with all improvements (6 aligners, retreat margin 30, scramble zone detection)

## Key Learnings
- Junctions outside ship range persist once aligned — focus on safe zones
- Ships are invisible to agents — must infer from junction flipping
- Score counts CONNECTED junctions (connectivity matters)
- Game is 10,000 steps, not 5,000
- High variance persists — some runs still score 0 (all agents die)
