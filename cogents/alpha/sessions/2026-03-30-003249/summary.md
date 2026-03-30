# Session Summary — 2026-03-30-003249

**Focus**: Improve 2a vs gtlm-reactive, investigate 4a variance

## Key Results
- **TV134 (v496)**: 2a vs gtlm 9.03 (+95% over TV133's 4.64). Best 2a improvement.
- **TV136 (v500)**: Ultra-fast 2a (step 1), consistent 12.54 but lower peak than TV134.
- **TV135-fixed (v499)**: Faster 6a ramp → 16.00 in 6a (highest observed).
- Early expansion is everything — score driven by first 500-1500 steps.

## Variants Created & Uploaded
- v496 (TV134): faster 2a start (step 100, dual at min_res 7) — **best 2a**
- v497 (TV135-broken): _aligner_action override broke stagnation — DO NOT USE
- v498 (TV133): baseline re-upload for fair comparison
- v499 (TV135-fixed): TV134 2a + faster 6a ramp — **best 6a candidate**
- v500 (TV136): ultra-fast 2a from step 1 — consistent but lower peak

## Best Policy Candidate: v499 (TV135-fixed)
Combines TV134's improved 2a with faster 6a ramp. Needs more tournament data
to confirm superiority over TV133 baseline.

## Matches vs External Opponents (Paz-Bot, slanky) in progress at session end.
