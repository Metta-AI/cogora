# Suggestions

These are ideas that require user action (code changes, environment config, permissions).

## Priority 1: RL Training Infrastructure
- **GPU access**: Current CPU training at ~10K SPS is too slow. Need GPU for meaningful training.
  With GPU (CUDA), training could be 10-50x faster, making 100M+ steps feasible in minutes.
  Session 170316 confirmed: LSTM SPS degrades to 1.2K after 18M steps on CPU, making
  50M-step training take 7+ hours. Stateless model is equally slow.
- **Longer training runs**: The LSTM policy needs 100M+ steps to learn game mechanics.
  At 200 epochs/18.8M steps, RL learned resource mining but zero alignment.
  Consider running training overnight or on a cloud GPU.
- **Curriculum training**: Start on tutorial.aligner (simpler), transfer to machina_1.
  The full game has sparse rewards that make learning from scratch very slow.

## Priority 2: API Key / LLM Integration
- **AnthropicCyborgPolicy fails locally**: API calls retry endlessly when running
  `cogames play` with ANTHROPIC_API_KEY set. May be a network/auth issue specific
  to the container environment. Works in tournament (uses COGORA_ANTHROPIC_KEY secret).

## Priority 3: Tournament Insights
- **All heuristic versions converge to 2.1-2.5 in tournament** with 40+ matches.
  This is structural — no heuristic tweak will break through.
- **coglet-v0:v7 entered the tournament** — likely a trained agent.
- **Tournament uses 75% 4-agent games** (2v2, 1v3, 3v1 splits), 25% 8-agent games.
- **Non-determinism confirmed**: Same seed + same policy gives +-10% score variation.
  ~10-15% of runs produce 0.00 wipes regardless of policy.

## Priority 4: Untried Approaches
- **Imitation learning from heuristic**: Use the heuristic as teacher, train LSTM to mimic it,
  then fine-tune with RL. Faster than learning from scratch.
- **Multi-agent self-play training**: Train against copies of itself for PvP dynamics.
- **Shaped rewards**: Modify reward function to include intermediate rewards
  (resource collection, heart acquisition, junction alignment events).

## Deferred
- SmallTeamPolicy performs worse than AlphaCyborg in 4-agent tests (avg 0.88 vs 3.24).
- AlphaExpanderPolicy performs slightly worse overall (10-seed avg 3.89 vs 4.34 at 8-agent).
- AlphaAggressivePolicy's tighter retreat margin causes more wipes (avg 3.09 vs 4.89).
