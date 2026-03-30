# Learnings — 2026-03-30-110959

## Adaptive Scramble is the Best Innovation (TV244 = #2 Overall)

v603 (TV244) = 14.73 (24m, #2 overall) vs TV235 (v594) = 14.57 (24m, #11).
The +0.16 improvement comes from a simple change: instead of fixed 50% stag
scramble, adapt based on junction balance:

- Behind 3+ junctions: scramble 75% of stag time (150/200)
- Even: scramble 50% (100/200, same as baseline)
- Ahead: scramble 25% (50/200)

This works because scrambling creates neutral junctions that can be realigned.
When behind, more scrambling creates more alignment opportunities. When ahead,
less scrambling preserves the lead.

## Decaying Peak Junction Count = Reliable but Smaller Gain

v598 (TV239 = TV191+decay) = 14.46 (24m, #15) vs v547 (TV191) = 14.69.
Surprisingly, decay actually *hurt* on TV191 base (-0.23) with full 24m data.
On TV208 base, v591 (TV233 = TV208+decay) = 14.72 vs v564 (TV208) = 14.51 (+0.21).

Conclusion: decaying peak helps on TV208 base but not on TV191 base.

## Combining Multiple Changes is Risky

- TV249 (v608): TV235+decay+3-tier+faster4a = 14.69 (14m) — decent but not better
  than TV244's single-change approach
- TV237 (v596): TV191+early aligner+less mining = 13.65 — confirmed bad combo
- TV246 (v605): TV240+dedicated scrambler = 9.80 — catastrophic

The safe approach is single-change variants from a proven base.

## What Works, What Doesn't

**Works:**
- Adaptive scramble intensity (TV244: +0.16 on TV235)
- Team-size stagnation (TV186: well-established)
- TV162 lower 6a thresholds (well-established)
- Lower 4a min_res to 15 (TV191: well-established)

**Doesn't work:**
- Dedicated scrambler agents (TV245/TV246: terrible, 12.02/9.80)
- Explore-only idle (TV243: 13.72, worse than baseline)
- Faster decay (300 steps) vs 500 (TV241: 13.56)
- Faster 6a stagnation entry (TV247: 14.12)

## Top Variants After 24+ Matches

1. v592 (TV234) = 14.82 (24m, #1) — pre-session champion
2. v603 (TV244) = 14.73 (24m, #2) — **session best**
3. v591 (TV233) = 14.72 (24m, #4) — pre-session
4. v547 (TV191) = 14.69 (81m, #5) — the true stable #1

## What to Try Next

1. **Adaptive scramble on TV191 base** (TV259 = v618, still qualifying)
2. **Adaptive scramble + decaying peak on TV191** (TV260 = v619, still qualifying)
3. **Tune scramble windows more precisely** (TV261/TV262 = v620/v621)
4. **LLM cyborg**: runtime strategy adaptation could push beyond ~15 ceiling
5. **Study gtlm-reactive and coglet-v0 strategies** from match logs
