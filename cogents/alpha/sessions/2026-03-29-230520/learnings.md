# Learnings — Session 2026-03-29-230520

## Critical Discovery: Cooperative Scoring
- Both teams in a match get the SAME score (cogs vs clips NPC).
- Both player policies are on the same "cogs" team.
- Leaderboard ranking = average score across all your matches.
- Implication: maximize total team performance, don't worry about "opponents."

## Dedicated Scramblers Are BAD
- Adding dedicated scrambler roles (always scramble, never align) is harmful.
- v484-v487, v491-v492, v494 all suffered from dedicated scramblers.
- 4a=3.5-6.8 with dedicated scramblers vs 13.5-14.0 without.
- Reason: aligners ALREADY scramble when idle (idle_align_scramble, stag_scramble).
  Dedicated scramblers steal alignment capacity in early game when it matters most.
- v489 (TV82 exact for 4a/6a) scored 4a=14.2, 6a=13.6 confirming TV82 is good.

## TV82's 4-Agent Budget Is Optimal
- AdaptiveV3 for 4 agents: 1 aligner (min_res<30) → 2 (min_res>=30) → 3 (min_res>=100)
- More aggressive ramp (TV131: 2 at min_res>=7, 3 at min_res>=30) HURTS.
  Drains economy too fast — hearts cost 7 of each resource, 1 miner can't keep up.
- Don't touch 4-agent budgets!

## Dual Aligner for 2-Agent Works
- v483 (TV122, dual aligner 2a) = 2a avg ~11.8 vs conservative (TV7) 2a avg ~6.7.
- v495 (TV133) confirms: 2a=11.9 with dual aligner.
- Reason: in 2v6, partner's 6 agents handle economy. Our 2 should both align.

## No-Scrambler for 6-Agent Helps
- v493 (TV131): 6a=14.0 with no dedicated scrambler (5 aligners + 1 miner).
- v495 (TV133): 6a=14.3 confirming.
- vs v489 (TV82 with scrambler): 6a=13.6.
- Removing the dedicated scrambler and adding an extra aligner = +0.4-0.7 in 6a.

## Early Expansion Matters Disproportionately
- Score = avg aligned junctions per tick across 10K steps.
- Early junctions contribute to more ticks → higher impact on average.
- In the 17.18 match, 11 junctions aligned by step 500 was the key.

## Best Policy: TV133 (v495)
- Minimal changes from TV82:
  1. 2-agent: dual aligner (both align when min_res >= 14)
  2. 5+ agents: replace dedicated scrambler with extra aligner
  3. 4-agent: EXACT TV82 (proven, don't touch)
- Result: 12.44 comp avg (44 matches), #1 with solid data.

## Opponent Analysis
- gtlm-reactive-v3: hardest opponent. 2a=4.64 against them.
- slanky:v112: decent partner, 13.04 avg but small sample.
- Paz-Bot-9005: 12.43 avg (5m), competitive.
- Old alpha versions (v11-v17): surprisingly good partners in 4v4 matches.
