# Suggestions

These are ideas that require user action (code changes, environment config, permissions).

## Priority 1: Tournament Match History Access
- **Need a way to query historical match results** — the `cogames matches` command only
  shows the 20 most recent matches. Completed v362 matches scroll off before I can see them.
  Consider: `cogames matches --policy alpha.0:v362` or `cogames leaderboard`.

## Priority 1.5: Fix num_agents Bug in All Tournament Versions
- **`policy_env_info.num_agents` is ALWAYS 8** (total agents in game), not team count.
  All TV90-TV108 used this for `num_agents <= 2` checks which NEVER fired.
  The correct way is `len(self._shared_team_ids)` (as TV81 does).
  TV109-TV111 are fixed. Consider backporting the fix to earlier versions if they're
  still relevant, or updating the base class to provide a `_team_size()` helper.

## Priority 2: Server Stability
- **Intermittent SSL certificate errors** prevent uploads and match checking.
  The cogames server has periodic SSL failures that block tournament interaction.
  Multiple retries with 30s+ delays sometimes help.

## Priority 3: RL Training Infrastructure
- **GPU access**: Current CPU training at ~10K SPS is too slow. Need GPU for meaningful training.
  With GPU (CUDA), training could be 10-50x faster, making 100M+ steps feasible in minutes.
- **The heuristic+scout approach may be near its ceiling** — RL could push further.

## Priority 4: Untried Approaches
- **Imitation learning from heuristic**: Use ScoutExplore as teacher, train LSTM to mimic it.
- **Multi-agent self-play training**: Train against copies of itself for PvP dynamics.
- **Better scout patterns**: Maybe learn optimal exploration routes from game data.

## Priority 5: Expand GitHub Repo Access
- **Add `metta-ai/metta` and `metta-ai/co-gas` to allowed GitHub repos** so Alpha can read
  competitor code (slanky, glanky, modular-lstm policies) for strategy analysis.
  Slanky code is at: `cog-cyborg/src/cogas_agents/policy/scripted_agent/slanky/`
  Glanky code is at: `cogas-agents/src/cogas_agents/policy/scripted_agent/glanky/`

## Deferred
- AnthropicCyborgPolicy fails locally (API calls retry endlessly in container).
- coglet-v0 and gtlm-reactive are real competitors — study their strategies.
