# Learnings — 2026-03-30-211500

## ALIGNER FLOOR: The Most Important Discovery
- The budget system drops to (1, 0) aligners during resource stress for 5+ agents
- This triggers a **death spiral**: fewer aligners → lose junctions → less score → more stress
- Match evidence: v822 (no floor) scored 0.71 vs modular-lstm; v832 (floor of 3) scored 7.37
- **Fix: NEVER drop below 2 aligners (5 agents) or 3 aligners (6+ agents)**
- Local testing confirmed: TV350 6-agent = 0.00 vs TV446 6-agent = 5.52

## Late-Game Decline Pattern
- All variants peak at ~11-15 junctions around step 600-900
- Then decline as enemy scrambles faster than we re-align
- By step 2000: friendly 5, enemy 17 (in local self-play)
- Key factor: stagnation explore is wasted time when no neutrals exist

## What Worked
- **TV446 (aligner floor of 3)**: Best overall, avg 2.28 local vs 1.70 baseline
- **TV442 (kitchen sink)**: Best local single run (2.11), but inconsistent
- **Scramble claim coordination**: Marginal improvement (+0.6% locally)
- **Proactive scramble when frontier=0**: Helps in combo (TV442) but hurts solo (TV440)

## What Didn't Work
- **TV440 (proactive scramble only)**: 1.41, worse than baseline — too aggressive
- **TV443 (mine when idle)**: 1.58, mining doesn't help if aligners are few
- **TV445 (kitchen sink + floor of 2)**: 1.76 local, but decent in competition

## Competition Results Summary (v831/v832)
v832 (TV446, best variant):
- 6v2 vs modular-lstm: 7.37, 3.24 (avg 5.31 — 7x better than v822's 0.71!)
- 6v2 vs Paz-Bot: 16.54 (BEATS v716's 15.05!)
- 6v2 vs swoopy: 12.73
- 2v6 vs Paz-Bot: 9.23
- Self-play: 15.17-16.53

v831 (TV445):
- 6v2 vs modular-lstm: 5.72
- 6v2 vs mammet: 9.31
- 4v4 vs Paz-Bot: 5.06
- 4v4 vs modular-lstm: 2.08

## Opponent Analysis
- **modular-lstm-bc:v13**: Strongest opponent. Even with aligner floor, scores 3-7 range
  - With just 2 agents they dominate junction control
  - Likely very efficient alignment + aggressive scrambling
- **Paz-Bot**: Weak. We score 9-16 against them
- **slanky**: Medium. 2-8 range
- **gtlm-reactive**: Medium. 7-12 range
- **swoopy**: Medium-weak. 8-12 range

## Variant Mapping
v826=TV440, v827=TV441, v828=TV442, v829=TV443
v830=TV444, v831=TV445, v832=TV446

## Next Steps
1. Get more competition data for v832 — need reliable average
2. Try higher aligner floor (4 for 8 agents?) — more alignment = more score
3. Study modular-lstm more closely — what makes 2 agents so effective?
4. Consider asymmetric strategy: different behavior when we're 2-agent vs 6-agent
5. RL training remains the long-term answer for breaking past heuristic ceiling
