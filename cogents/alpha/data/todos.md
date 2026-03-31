# Todos

- [x] **GOAL ACHIEVED**: Score > 10 in tournament — v873 (TV478) avg 10.13
- [x] Aligner floor for 5+ agents + 4v4 floor: TV488/v884 best overall (avg 9.58)
- [x] Fix shared_team_ids in PilotCyborgPolicy — role assignment for team 2
- [x] Add [COG] logging to AnthropicPilotAgentPolicy
- [x] Team-size budget: REGRESSED (v900 avg ~1). Reverted. Budget MUST use total num_agents.
- [ ] **Check v903 + v901 competition results** — v903 = proven budget + mining stall fix
- [ ] **Mining stall detection** — added, needs tournament validation. May help silicon/germanium death spiral.
- [ ] **Heuristic ceiling confirmed at ~10** — v884 avg 9.58. ALL budget/stagnation mods regress.
- [ ] **RL training** — HIGHEST PRIORITY. Only way to break heuristic ceiling. Need GPU.
- [ ] **Shared extractor with target claims** — miners claim extractors to avoid clustering.
- [ ] **Study opponent strategies** — coglet, mammet, modular-lstm, gtlm-reactive.
- [ ] **CRITICAL**: Budget num_agents = policy_env_info.num_agents (total=8), NOT team size.
- [ ] **CRITICAL: Qualifying ≠ Competition** — qualifying avg != competition avg.
