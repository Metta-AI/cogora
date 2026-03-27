# CogsVsClips Development Setup

## Environment Setup

The system has Python 3.11 but `cogames` requires Python 3.12. Setup:

```bash
# Install Python 3.12 via uv
uv python install 3.12

# Create a venv with Python 3.12 for running cogames
uv venv --python 3.12 .venv-cogames

# Install cogames and the local package
uv pip install cogames --python .venv-cogames/bin/python
uv pip install -e . --python .venv-cogames/bin/python
```

## Running Games Locally

```bash
# Run with your policy (8 cogs, full game)
.venv-cogames/bin/cogames play -m machina_1 -c 8 -p class=cvc_cog.alpha_policy.AlphaPolicy -r log --autostart > /tmp/cogames/latest.log 2>&1

# Shorter test (100 steps)
.venv-cogames/bin/cogames play -m machina_1 -c 8 -p class=cvc_cog.alpha_policy.AlphaPolicy -r log --autostart --steps=100 > /tmp/cogames/latest.log 2>&1

# Run with starter policy for comparison
.venv-cogames/bin/cogames play -m machina_1 -c 8 -p starter -r log --autostart --steps=5000 > /tmp/cogames/starter.log 2>&1
```

## Uploading to Tournament

```bash
.venv-cogames/bin/cogames upload -p cvc-cog -n alpha.0 --skip-validation
```

## Checking Results

```bash
.venv-cogames/bin/cogames matches
.venv-cogames/bin/cogames matches <match-id>
.venv-cogames/bin/cogames matches <match-id> --logs
.venv-cogames/bin/cogames match-artifacts <match-id>
```

## Key Issues Hit During Setup

1. **Python version mismatch**: cogames requires `>=3.12,<3.13`. System has 3.11. Solution: `uv python install 3.12`.
2. **mettagrid_sdk not available**: The `mettagrid_sdk` package used in `cvc_cog/policy/semantic_cog.py` is not on PyPI. The policy must use the raw token-based observation API from `mettagrid.simulator.interface.AgentObservation`.
3. **Policy class path**: Use `class=cvc_cog.alpha_policy.AlphaPolicy` format. Short names like `starter` only work for built-in policies.

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

## Architecture

- `src/cvc_cog/alpha_policy.py` - Main policy file
- Policy extends `MultiAgentPolicy` -> `agent_policy(agent_id)` -> `AgentPolicy.step(obs)`
- Observations are token-based: each token has `feature.name`, `value`, and `location`
- Tags identify entity types: `type:junction`, `type:hub`, `team:cogs`, `net:cogs`, etc.
- Inventory: `inv:heart`, `inv:aligner`, `inv:carbon`, etc.
