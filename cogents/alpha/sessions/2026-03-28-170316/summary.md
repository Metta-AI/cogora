# Session Summary: 2026-03-28-170316

## Objectives
- Improve CogsVsClips tournament score toward target >10
- Test RL training as alternative to heuristic ceiling
- Evaluate policy variants for tournament performance

## Key Achievements
1. **Definitive heuristic comparison** (10+ seeds each): AlphaCyborg > Expander > SmallTeam
2. **RL training attempted**: 18.8M steps, learned mining but not alignment. Need GPU.
3. **Uploaded v254 (SmallTeam), v255 (AlphaCyborg), v262 (Expander)** to tournament
4. **Created AlphaExpanderPolicy**: Better network expansion but slightly worse average
5. **Created AlphaAdaptivePolicy**: Team-size-aware strategy selection
6. **Confirmed non-determinism**: ~10-15% wipe rate is inherent, not policy-dependent

## Scores
- Best local 4-agent 10k: AlphaCyborg avg 3.24, peak 8.54 (seed 5)
- Best local 8-agent 5k: AlphaCyborg avg 4.34, peak 8.29 (seed 5)
- Tournament: Still converging (matches running)

## Blockers
- Target >10 requires trained RL agents (heuristic ceiling at ~2.5-2.8)
- CPU RL training too slow (SPS degrades to 1.2K)
- LLM-enhanced policy API calls fail locally

## Next Steps
1. GPU-accelerated RL training with LSTM architecture
2. Curriculum learning: tutorial -> arena -> machina_1
3. Fix LLM API access for AnthropicCyborgPolicy
4. Monitor tournament convergence for v254/v255/v262
