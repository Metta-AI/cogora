# Suggestions

<!-- Log ideas and requests that only the user can action (source changes, env config, permissions, etc.) -->

## High Priority
- **Territory-aware pathfinding**: A* currently costs 1 per cell. Outside territory, movement costs 4x. Making A* weight non-territory cells at 4 would route agents through territory, reducing deaths and increasing speed. This requires tracking which cells are in territory (within 10 tiles of hub/aligned junctions).
- **Adaptive scrambler**: Current 1-scrambler approach helps ship-dominated maps (+147-326%) but hurts favorable maps (-69%). Need a smarter activation heuristic — maybe track actual scramble rate of our junctions over last 200 steps.

## Urgent
- **Investigate v65's frozen dependencies**: v65 was uploaded with older cogames/mettagrid versions. ALL new versions (v200+) converge to 2.0-2.3 while v65 stays at 3.59. The gap is NOT in strategy (even vanilla base = 2.15). It's likely in a game engine or SDK behavior change. Check if `cogames`/`mettagrid` dependency versions changed between v65's upload and now. If the game mechanics changed (e.g., alignment range, resource costs, HP drain rate), that would explain everything.
- **Try uploading with older dependency versions**: If cogames/mettagrid updated, pin the older version in setup_policy.py and see if it recovers v65-level performance.

## Medium Priority
- **Shared extractor knowledge**: Currently each agent has its own WorldModel. Sharing extractors across agents would reduce redundant exploration. Challenge: prune_missing_extractors conflicts with shared model (agent A prunes extractors only visible to agent B). Could use a per-agent visibility check or skip pruning entirely.
- **Early-game optimization**: The first 200 steps are critical for score accumulation. Currently 2 aligners start, expanding to 5 at step 30. Consider whether more aggressive early alignment (more aligners earlier) would improve score despite economy trade-off.
