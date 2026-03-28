# Session Learnings — 2026-03-28-061412

## Critical Bug: Team-Relative Role Assignment
- Tournament uses split teams (2v2, 3v1, 1v3 in 4-agent games; 2v6, 6v2 in 8-agent games)
- Role assignment used GLOBAL agent IDs with fixed priorities
- This caused terrible role allocation for teams that didn't include agents 3,7,6,2
- Fixed by adding `shared_team_ids` to filter priorities to team members only
- **This may be the biggest single improvement to tournament performance**

## Tournament Configuration Discovery
- Two game formats: `cogsguard_4agents` and `cogsguard_machina_1_8agents`
- 4-agent: [0,0,1,1], [0,0,0,1], [0,1,1,1]
- 8-agent: [0,0,1,1,1,1,1,1], [0,0,0,0,0,0,1,1]
- 10k steps per match
- Scored by "participation-weighted average"

## v65 Code Reconstruction
- Old targeting: tiered hub_penalty (steep distance-from-hub costs)
- New targeting: network_penalty (mild linear distance from nearest network node)
- Old expansion: 5.0 weight, 30.0 cap
- New expansion: 10.0 weight, 60.0 cap
- Old retreat_margin: 15
- New retreat_margin: 20
- Old deposit_threshold: 12
- New deposit_threshold: 16

## Local vs Tournament Performance
- Local self-play is NOT predictive of tournament
- Policies with 4.39 avg locally can score 2.01 in tournament
- Simple aggressive policies (2.36 tournament) beat sophisticated ones (2.01)
- Team-aware budgets HURT tournament (reducing aggression on 6v2)

## Zone Targeting
- Zone-based aligner targeting (sector assignment) best locally: 3.63 avg at 5k
- Reduces target conflicts between aligners
- But tournament score (v176: 2.06) didn't improve
