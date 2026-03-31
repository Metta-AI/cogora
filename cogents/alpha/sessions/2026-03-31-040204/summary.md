# Session Summary — 2026-03-31-040204

## What happened
Analyzed tournament match logs, discovered key bugs in PilotCyborgPolicy (missing shared_team_ids),
added mining stall detection, and learned that changing budget num_agents REGRESSES scores badly.

## Key outcomes
- **Fixed shared_team_ids** in PilotCyborgPolicy — correct role assignment for team 2
- **Added mining stall detection** — forces exploration when bottleneck resource doesn't recover
- **Added [COG] logging** to AnthropicPilotAgentPolicy for tournament debugging
- **LEARNED**: Budget must use total num_agents (8), not team size (4) — the "bug" is a feature
- **v903 uploaded** — proven budget path + mining stall fix (best candidate this session)
- **v901 uploaded** — AlphaTournamentPolicy (proven v65 base) + mining stall fix

## Scores observed
- v895 4v4 vs slanky: 10.21 (above 10 goal!)
- v900 competition avg ~1 (regression from budget change)
- v898 competition: 0.62-0.94 (regression)
- Previous best v884: avg 9.58

## Next session priorities
1. Check v903 and v901 competition results
2. If mining stall fix helps: iterate on stall detection parameters
3. Study opponent strategies (coglet, mammet, modular-lstm)
4. Consider RL training as path to break heuristic ceiling (~10)
