# Suggestions

These are ideas that require user action (code changes, environment config, permissions).

## Priority 1: RL Training Infrastructure
- **GPU access**: Current CPU training at ~10K SPS is too slow. Need GPU for meaningful training.
  With GPU (CUDA), training could be 10-50x faster, making 100M+ steps feasible in minutes.
- **Longer training runs**: The LSTM policy needs 100M+ steps to learn game mechanics.
  Consider running training overnight or on a cloud GPU.
- **Curriculum training**: Start on tutorial.aligner (simpler), transfer to machina_1.
  The full game has sparse rewards that make learning from scratch very slow.

## Priority 2: Tournament Insights
- **All heuristic versions converge to 2.1-2.2 in tournament** with 40+ matches.
  This is structural — no heuristic tweak will break through.
- **coglet-v0:v8 entered at 3.02** — likely a trained agent. Shows trained agents CAN
  score higher than the heuristic ceiling.
- **Tournament uses 75% 4-agent games** (2v2, 1v3, 3v1 splits), 25% 8-agent games.

## Priority 3: Untried Approaches
- **Imitation learning from heuristic**: Use the heuristic as teacher, train LSTM to mimic it,
  then fine-tune with RL. Faster than learning from scratch.
- **Multi-agent self-play training**: Train against copies of itself for PvP dynamics.
- **Shaped rewards**: Modify reward function to include intermediate rewards
  (resource collection, heart acquisition, junction alignment events).

## Deferred
- SmallTeamPolicy showed 33% improvement in local tests but tournament shows same ceiling.
  May still help if tournament converges further — need 100+ matches.
