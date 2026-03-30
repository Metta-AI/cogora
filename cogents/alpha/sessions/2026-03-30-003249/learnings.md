# Learnings — Session 2026-03-30-003249

## TV134: Faster 2a Start Works (+95% vs gtlm-reactive)
- TV133 waited 200 steps before first aligner in 2a mode, dual at min_res >= 14
- TV134 starts at step 100, dual at min_res >= 7
- vs gtlm-reactive 6a: 9.03 (TV134) vs 4.64 (TV133) = +95% improvement!
- vs v38 6a: 15.10 (TV134) vs ?? (TV133)
- The earlier start captures more early-game junctions which disproportionately
  affect the average score (more ticks counted)

## TV136: Ultra-Fast 2a (Step 1) is Consistent but Not Best
- TV136 aligns from step 1 (no mining wait at all), always dual
- Produces very consistent 12.54 across all tested opponents
- But TV134 has higher peak performance (15.10 vs 12.54 against v38)
- Hypothesis: some mining in the first 100 steps builds a small economy buffer
  that helps sustain longer alignment runs. Pure alignment from step 1 is
  too aggressive — agents run out of hearts faster.

## TV135-Fixed: Faster 6a Ramp Shows Promise
- Faster 6a aligner ramp (min_res 50/100 vs TV133's 80/200)
- v499 6a vs v44 2a = 16.00 (highest 6a score observed)
- More aligners sooner in rich economy → faster expansion
- Doesn't hurt 4a (identical budgets)

## Early Expansion is Everything
- Score = avg aligned junctions per tick across 10K steps
- A junction aligned at step 500 contributes to 9500+ ticks
- A junction aligned at step 5000 contributes to only 5000 ticks
- Match analysis: 14.97 score match had 8-13 junctions by step 500,
  even though ALL were lost by step 10K. Early dominance = high average.
- Late-game collapse to clips NPCs is inevitable — optimize early game.

## Score Determinism and Map Seeds
- Same matchup (same 2 policies, same team sizes) produces identical scores
- v500 2a vs v34/v35/v38 all = 12.54 (exactly)
- v496/v498 4a vs v38 = 9.92 (exactly)
- Implies fixed map seeds per match configuration
- Single-match results are meaningful (not just noise)

## Auto-Upload Mechanism
- Pushing to main auto-uploads using AnthropicCyborgPolicy class
- These auto-uploads (v51-v56) have different budgets than tournament variants
- Must manually upload with specific class paths for TV133/TV134/etc.
- Auto-uploaded AnthropicCyborgPolicy has 1 aligner for 2a (no dual), which is
  worse than TV133/TV134's dual aligner

## Partner Quality Dominates Scores
- In 2v6 format, the 6-agent partner is the dominant factor
- Bad 2a partners (v455-v487 with scrambler bugs) drag entire team to 1-6
- Our control: make all our configurations (2a, 4a, 6a) strong independently
- Leaderboard avg includes ALL matchups — bad partner matches hurt

## Version Summary
- v496 (TV134): faster 2a (step 100, dual at min_res 7) — best overall
- v497 (TV135-broken): DO NOT USE — _aligner_action override removed stagnation logic
- v498 (TV133): baseline, proven at 12.44 comp avg
- v499 (TV135-fixed): TV134 2a + faster 6a ramp — promising, needs more data
- v500 (TV136): ultra-fast 2a from step 1 — consistent but lower peak
