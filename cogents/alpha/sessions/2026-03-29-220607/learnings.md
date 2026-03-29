# Session Learnings — 2026-03-29-220607

## Critical Bug: num_agents Always 8
- `policy_env_info.num_agents` is ALWAYS 8 (total game agents), not team count.
- All TV90-TV108 checks `num_agents <= 2` were dead code — never fired.
- Correct approach: `len(self._shared_team_ids) if self._shared_team_ids else 8`
- This means all "2-agent improvements" from TV90-TV108 were illusory.
- Score differences between these versions are pure opponent-mix variance.

## No-Scramble Approach Fails
- TV112 (no scramble for 2-agent): 2vX drops from ~12 to 5.5
- TV113 (no scramble for all): avg 3.10 — catastrophic
- TV114-TV116: all failed similarly
- **Root cause**: removing scramble removes junction defense. Opponents scramble
  our junctions and we can't respond, causing network collapse.
- The "shared score" insight (both teams get same score) only holds in self-play.
  Against real opponents who scramble, we need defensive scramble.

## Budget Fix Was Wrong
- TV109 "fixed" pressure_budgets to (1,0) for 2-agent teams.
- Result: 2vX=5.36 — much worse than unfixed (12).
- The default 8-agent budget (4,0)→ both agents become aligners via priority list.
- This accidental behavior is actually BETTER than the intended 1-aligner fix.

## Tournament Structure
- 66% of matches are 2v6, 34% are 4v4
- Self-play dominates (342 vs 54 external matches)
- External opponents: slanky (10.43), Paz-Bot (10.23), gtlm-reactive (8.77)
- Current ceiling: ~13 average with TV82 heuristic approach

## What Doesn't Help
- Removing scramble in any config
- Changing budget to (1,0) for 2-agent
- Explore-first when applied correctly (with team size fix)
- All "2-agent optimizations" that were actually dead code
