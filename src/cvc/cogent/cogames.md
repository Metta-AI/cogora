# CogsVsClips Development Setup

## Environment Setup

Run `src/cvc/setup.sh` for one-time setup (installs Python 3.12 venv, cogames, auth).

Auth requires `COGAMES_TOKEN` in env. If not authenticated, run:
```bash
cogames auth set-token $COGAMES_TOKEN
```

## Running Games Locally

```bash
# Run with your policy (8 cogs, full game)
cogames play -m machina_1 -c 8 -p class=cvc.cogent.player_cog -r log --autostart > /tmp/cogames/latest.log 2>&1

# Shorter test (100 steps)
cogames play -m machina_1 -c 8 -p class=cvc.cogent.player_cog -r log --autostart --steps=100 > /tmp/cogames/latest.log 2>&1

# Run with starter policy for comparison
cogames play -m machina_1 -c 8 -p starter -r log --autostart --steps=5000 > /tmp/cogames/starter.log 2>&1
```

## Uploading to Tournament

```bash
# IMPORTANT: Must use full class path and include source directories
cogames upload -p "class=cvc.cogent.player_cog.policy.semantic_cog.MettagridSemanticPolicy" -n alpha.0 -f src/cvc -f src/mettagrid_sdk --skip-validation
```

## Checking Results

```bash
cogames auth status
cogames matches
cogames matches <match-id>
cogames matches <match-id> --logs
cogames match-artifacts <match-id>
```

## Tournament Workflow

After validating changes in free-play, enter the tournament:

1. **Upload**: Submit your policy (increment the version number each time):
   ```bash
   cogames upload -p "class=cvc.cogent.player_cog.policy.semantic_cog.MettagridSemanticPolicy" -n alpha.N -f src/cvc -f src/mettagrid_sdk --skip-validation
   ```
2. **Wait for matches**: Tournament runs matches automatically. Check status:
   ```bash
   cogames matches
   ```
3. **Analyze results**: Review your match scores and compare against opponents:
   ```bash
   cogames matches <match-id>
   cogames matches <match-id> --logs
   cogames match-artifacts <match-id>
   ```
4. **Study opponents**: Read match logs to see how other Cogents play.
   Look for strategies you haven't tried — what roles do they use,
   how do they handle scrambling, what's their economy approach?
   Record opponent insights in `learnings.md`.
5. **Iterate**: Use tournament results and opponent analysis to guide
   your next round of free-play experimentation.

Upload regularly — tournament signal is more valuable than local testing
alone. Other Cogents reveal strategies you can't discover in self-play.

## Key Issues Hit During Setup

1. **Python version mismatch**: cogames requires `>=3.12,<3.13`. System has 3.11. Solution: `uv python install 3.12`.
2. **mettagrid_sdk not available**: The `mettagrid_sdk` package used in `cvc/cogent/player_cog/policy/semantic_cog.py` is not on PyPI. The policy must use the raw token-based observation API from `mettagrid.simulator.interface.AgentObservation`.
3. **Policy class path**: Use `class=cvc.cogent.player_cog` format. Short names like `starter` only work for built-in policies.

## Game Mechanics Quick Reference

- **Score**: avg number of aligned junctions in team network per tick
- **Alignment**: Aligner walks onto neutral junction within range 15 of network (or 25 of hub). Costs 1 heart.
- **Scramble**: Scrambler walks onto enemy junction. Costs 1 heart.
- **Gear stations**: Walking onto a station auto-gives that gear. Stations are near hub.
- **Gear cost**: Hub resources are consumed when getting gear (e.g., aligner costs carbon:3, oxygen:1, germanium:1, silicon:1)
- **Hearts**: Get hearts by walking onto hub. Costs 7 of each element from hub.
- **Deposits**: Walk onto hub/friendly junction with resources to auto-deposit.
- **Observation**: 13x13 grid of tokens with tags, inventory, etc.
- **Map**: 88x88 with walls, ~65 junctions, ~200 extractors.
- **Hub initial resources**: num_agents * 3 of each element = 24 each for 8 agents.

## Policy Logging

Instrument the policy with print-based logging so you can learn from game
replays. After a `cogames play` run, read the log file to extract experience.

Key things to log (prefix all lines with `[COG]` for easy grep):
- **Per-step**: agent id, position, action taken, inventory summary
- **Decisions**: why a target was chosen, what alternatives were considered
- **Events**: aligned a junction, got scrambled, picked up gear, deposited resources
- **Periodic summary** (every ~100 steps): score, total alignments, resources in hub

After a game, extract learnings:
```bash
grep '\[COG\]' /tmp/cogames/latest.log | tail -200
```

Record insights in `activity.log` and `learnings.md`. This is how you
build understanding of what strategies work.

## Architecture

- `src/cvc/cogent/player_cog/` - Main policy package
- Policy extends `MultiAgentPolicy` -> `agent_policy(agent_id)` -> `AgentPolicy.step(obs)`
- Observations are token-based: each token has `feature.name`, `value`, and `location`
- Tags identify entity types: `type:junction`, `type:hub`, `team:cogs`, `net:cogs`, etc.
- Inventory: `inv:heart`, `inv:aligner`, `inv:carbon`, etc.
