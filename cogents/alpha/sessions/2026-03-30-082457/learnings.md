# Learnings — 2026-03-30-082457

## v557 (TV201) Was a Disaster at 9.90

TV201 combined TV162 6a + TV186 stag + TV198 "always-2-aligners" 4a.
Per-team-size: 2a=3.80, 4a=6.52, 6a=12.95 (431 matches).

Root cause: TV198's "always 2 aligners" for 4a skips the economy ramp
entirely (`aligner_budget = 2` immediately). This crashes the economy
in 4a where starting resources are only 12 each (4 agents × 3).

**Lesson**: Economy gates are essential for 4a. Never skip the min_res
check before adding a 2nd aligner.

## v547 (TV191) Strengths and Weaknesses

v547 = #1 at 14.66 (78 matches): 2a=13.97, 4a=13.45, 6a=15.71.

Weakness analysis for 4a (avg 13.45):
- Excellent vs old alpha (16.06): v11-v17, v29-v31, v50-v51
- Good vs mid-tier (12-15): v34-v55
- Weak vs externals: gtlm=6.99, Paz-Bot=11.30, slanky=11.85
- Terrible vs v56=7.85, v47=10.90

gtlm cooperative scoring: both teams get same score. gtlm's aggressive
scrambling hurts both sides. Our 6a agents can partially compensate
(11.37 when we have 6a vs gtlm 2a).

## 8 New Variants Created and Uploaded (v558-v565)

### Targeting 4a weakness:
- **TV202 (v558)**: min_res 12 (was 15) — faster 2nd aligner
- **TV203 (v559)**: earlier 3rd aligner at 60/200 (was 80/300)
- **TV204 (v560)**: step<30 initial ramp (was step<50)
- **TV205 (v561)**: all 4a improvements combined

### Targeting 6a:
- **TV206 (v562)**: 3-tier stagnation (medium for 6a: peak 4, 250 steps, min 400)
- **TV207 (v563)**: lower 6a thresholds (22/35/70 vs 25/40/80)

### Combined:
- **TV208 (v564)**: TV206 stag + TV207 thresholds
- **TV209 (v565)**: full combo (TV202 4a + TV207 6a + TV206 stag)

## Early Competition Results (ALL vs v557 only — will change)

| Variant | Description | Score | Rank |
|---------|-------------|-------|------|
| v565 (TV209) | Full combo | 16.33 | #1 |
| v564 (TV208) | 6a combo | 16.21 | #2 |
| v563 (TV207) | Lower 6a thresh | 16.04 | #3 |
| v558 (TV202) | 4a min_res 12 | 15.51 | #4 |
| v560 (TV204) | 4a faster ramp | 15.39 | #5 |
| v561 (TV205) | All 4a | 15.05 | #6 |
| v562 (TV206) | 3-tier stag | 14.83 | #7 |
| v559 (TV203) | Earlier 3rd | 14.27 | #16 |

**WARNING**: These scores are inflated because all matches are vs v557
(9.90 avg). Real performance will be determined when matched against
v547, v542, slanky, gtlm etc. Expect significant convergence downward.

## Key Insights for Next Session

1. **6a improvements more impactful than 4a**: TV207 (6a thresholds) and
   TV206 (6a stagnation) both ranked higher than 4a-only changes.

2. **Combining improvements stacks well**: v565 (TV209, full combo) > v564
   (TV208, 6a only) > v563 (TV207, thresholds only).

3. **Silicon is the early bottleneck**: In 4a games, silicon drops to 8 at
   step 100 while others reach 46-68. The min_res gate is blocked by
   silicon, not the threshold value. Lowering from 15 to 12 may not help.

4. **Upload efficiency**: Including .venv-cogames in bundle caused 7GB
   upload. Fixed by specifying individual files/dirs (671KB bundle).

## What to Monitor Next

- v565 (TV209) and v564 (TV208) convergence with diverse opponents
- Whether 6a improvements hold against strong 6a opponents
- Whether 4a min_res 12 actually helps or is noise
- v559 (TV203, earlier 3rd aligner) is weakest — may confirm that
  3rd aligner transition is not the bottleneck
