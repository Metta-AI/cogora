# Learnings — 2026-03-31-040204

## CRITICAL: Don't Change Budget num_agents!
- The policy uses `policy_env_info.num_agents` (total=8) for budget calculations
- This puts 4v4 matches (4 agents per team) into the 5+ agent path
- The 5+ path is MORE AGGRESSIVE (3-5 aligners) than the 4-agent path (1-2 aligners)
- v884 (avg 9.58) was BUILT on this "bug" — changing to team-size budgets REGRESSED to avg ~1
- Keep `num_agents = self.policy_env_info.num_agents` in ALL budget functions

## shared_team_ids Fix IS Correct
- PilotCyborgPolicy.agent_policy() was missing shared_team_ids → role assignment used global IDs
- For team 2 (IDs 4-7), the global `_SCRAMBLER_PRIORITY = (3, 7, 6, 2)` would wrongly assign
  agent 7 as scrambler and agents 4,5,6 wouldn't match expected roles
- Fix: pass shared_team_ids through PilotAgentPolicy to SemanticCogAgentPolicy
- This fixes ROLE ASSIGNMENT, not budget (budget should keep total num_agents)

## Mining Stall Detection
- Added to AlphaCogAgentPolicy, AnthropicPilotAgentPolicy, and AlphaTournamentAgentPolicy
- When bottleneck resource doesn't improve for 50 steps AND is < 7, force exploration
- Uses agent_id offset to spread miners in different directions
- Should help break the silicon/germanium death spiral on resource-scarce maps

## Economy Death Spiral Is Map-Dependent
- Same policy: 13.76 on one map, 1.54 on another (4v4)
- Silicon/germanium extractors are scarce on some maps
- Miners converge on same depleted extractors → resources never recover
- Hub can't make hearts when ANY element < 7 → all pressure agents stuck in rebuild_hearts
- The death spiral is self-reinforcing: no hearts → can't align → lose territory → can't recover

## [COG] Logging Added to AnthropicPilotAgentPolicy
- Tournament uses AnthropicCyborgPolicy but previously had no [COG] logging
- Added evaluate_state override with same logging format as AlphaCogAgentPolicy
- Enables debugging tournament matches

## v900 Competition Results (REGRESSION)
- v900 avg ~1.0 (terrible) — caused by team-size budget change
- Most matches were 2v6 which are structurally hard (2 agents vs 6)
- 4v4 vs random-assay: 1.97 — far below v884's avg 9.58
- Root cause: budget with num_agents=4 enters conservative 4-agent path instead of aggressive 5+ path

## Versions Uploaded This Session
- v897: AnthropicCyborgPolicy (LLM) — team-size budgets (REGRESSION)
- v898: AlphaCyborgPolicy — team-size budgets (REGRESSION) — qualified, competition avg ~1
- v899: AnthropicCyborgPolicy (LLM) — + mining stall fix
- v900: AlphaCyborgPolicy — + mining stall fix (REGRESSION in competition ~1)
- v901: AlphaTournamentPolicy — mining stall fix only (proven base)
- v902: AlphaCyborgPolicy — conservative 5+ budget (might regress)
- v903: AlphaCyborgPolicy — reverted budget to proven path + mining stall fix (BEST CANDIDATE)
