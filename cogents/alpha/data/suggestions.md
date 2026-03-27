# Suggestions

<!-- Log ideas and requests that only the user can action (source changes, env config, permissions, etc.) -->

## High Priority
- **Territory-aware pathfinding**: A* currently costs 1 per cell. Outside territory, movement costs 4x. Making A* weight non-territory cells at 4 would route agents through territory, reducing deaths and increasing speed. This requires tracking which cells are in territory (within 10 tiles of hub/aligned junctions).
- **Adaptive scrambler**: Current 1-scrambler approach helps ship-dominated maps (+147-326%) but hurts favorable maps (-69%). Need a smarter activation heuristic — maybe track actual scramble rate of our junctions over last 200 steps.

## Medium Priority
- **Shared extractor knowledge**: Currently each agent has its own WorldModel. Sharing extractors across agents would reduce redundant exploration. Challenge: prune_missing_extractors conflicts with shared model (agent A prunes extractors only visible to agent B). Could use a per-agent visibility check or skip pruning entirely.
- **Early-game optimization**: The first 200 steps are critical for score accumulation. Currently 2 aligners start, expanding to 5 at step 30. Consider whether more aggressive early alignment (more aligners earlier) would improve score despite economy trade-off.
