# Learnings — 2026-03-30-180756

## Confirmed: Heuristic ceiling at ~15.05
- TV350 (hotspot=-10, 7a@120) is the optimal heuristic configuration
- Fine-tuning any parameter (retreat threshold, heart batching, expansion weight, deposit threshold, target stickiness) makes things WORSE
- Budget tuning for 4-agent games also harmful
- The heuristic policy is at a local maximum

## Local testing is unreliable
- Density variants scored +86% locally but -35% in tournament
- This is because local tests play against Clips AI (scripted opponent)
- Tournament matches are against other Cogents with different strategies
- Always validate in tournament, never trust local-only results

## Variant mapping for this session
- v775-v785: Fine-tuning around TV350 (hotspot, expansion, budgets)
- v786-v796: Structural changes (retreat, hearts, deposit, stickiness)
- v797: LLM cyborg with TV350 base (paradigm shift attempt)

## What didn't work
- Lower aligner retreat threshold (v786): 7.88
- expansion_weight changes (v790): 2.18
- hotspot=-11 (v785): 13.15
- expansion_weight=12 (v783): 13.33

## Path forward
- LLM cyborg (v797) is the most promising next step
- If cyborg shows improvement, iterate on LLM parameters (model, temperature, review frequency)
- Alternatively: opponent modeling, asymmetric team strategies
