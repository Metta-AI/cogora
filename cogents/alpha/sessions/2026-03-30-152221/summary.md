# Session Summary — 2026-03-30-152221

**Heuristic ceiling confirmed at 14.94 (v632/TV272, 33 matches).**

Created 19 new variants (TV322-TV340, v684-v702) testing:
- Hub-proximity scramble, faster ramp, no-scramble, mine-during-stag (all worse)
- Re-align bonus on TV272 base (marginal +0.1)
- Different hotspot weights (-4, -8, -12, -16) — all converge to same range
- 7th aligner thresholds (110, 120, 130) — 150 is optimal
- Combined innovations from top 2 variants

Key finding: all parameter tuning converges to 14.6-14.9 with enough matches.
Early match scores (4-10m) are very noisy — v687 spiked to 16.29 but settled to 14.66.
Need fundamentally different approach (LLM cyborg) to break ceiling.

## Variants Created
TV322-TV340 (v684-v702):
- TV322-TV325: hub-proximity, faster ramp, no-scramble, no-stag-scramble
- TV326-TV330: TV272+re-align combos, wider scramble, mine-stag
- TV331-TV335: re-align weight tuning (-4,-8,-12,-16), 7a@120, bottleneck+re-align
- TV336-TV340: fine-tuning around TV334 (7a@110/120/130, 6a@80, faster decay)
