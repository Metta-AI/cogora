# Learnings — Session 2026-03-29-121717

## Tournament vs Local Play
- **Silicon priority**: Hurts in 8-agent self-play (TV18 scored 0.09 on seed 0!) but
  helps massively in 4v4 tournament (10.15 vs 8.69 without). The opponent creates
  resource pressure that doesn't exist in self-play.
- **Early-game hub_camp_heal**: Territory healing works in tournament but not locally
  (different mettagrid version or config). Removing it costs ~1.5 points in tournament.
- **Conclusion**: Always validate in tournament, not just self-play.

## Stagnation Detection
- TV12's default stagnation (300 steps, peak >= 5) is well-tuned.
- Faster trigger (200 steps, TV22) = 7.72 — HURTS. Premature exploration.
- TV25's scramble-focused stagnation is promising in self-play (+24%).
- Far stagnation explore (radius 22-35) wastes HP — regular explore is better.

## Code Quality
- mettagrid SDK version 0.21.1 — territory healing confirmed to be +100 HP/tick
  within 10 tiles of hub (20 tiles) and friendly junctions (10 tiles).
- Hub territory radius is 2x normal (20 tiles, not 10).
- Junction AOE range is 10 tiles, not 15 as coded in some constants.

## Leaderboard Dynamics
- New policy scores are volatile with <30 matches.
- Scores stabilize by 80+ matches.
- Early scores (2-20 matches) can be 2+ points off from true performance.
- Opponent pool evolves — same policy can score differently as pool changes.
