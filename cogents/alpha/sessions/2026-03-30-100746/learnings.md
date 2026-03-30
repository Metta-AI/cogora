# Learnings — 2026-03-30-100746

## TV191 (v547) is the True #1, Not TV208 (v564)

With 81 matches, TV191 = 14.69 vs TV208 = 14.51 (24m). The previous
session's conclusion that TV208 was best was based on fewer matches.
TV208's lower 6a thresholds (22/35/70 vs 25/40/80) and 3-tier stagnation
actually hurt slightly vs TV191's simpler approach.

## Early 3rd Aligner (Step 15) = Consistent Improvement

For 5+ agent teams, allowing a 3rd aligner at step >= 15 (instead of 30)
when starting resources are still flush (min_res >= 20) consistently helps:
- v585 (TV228, on TV208 base): #7 at 14.63 (24m) — solid
- v594 (TV235, on TV191 base): #1 at 14.90 (23m) — best!

The extra 15 steps of 3-aligner expansion captures more junctions early,
which compounds over 5000 steps. Starting resources (24 each) are sufficient.

## Decaying Peak Junction Count = Genuine Fix

v591 (TV233): #4 at 14.72 (24m), beats v547's 14.69 (81m).
v592 (TV234, combined with early aligner): #2 at 14.82 (24m).

Problem fixed: once peak_junction_count is set high and junctions are lost,
stagnation never exits. The decay (peak -= 1 every 500 stagnation steps)
allows the policy to "forget" old peaks and try fresh expansion cycles.

## Less Idle Mining: Small Benefit When Combined, Negative Alone

| Variant | Description | Score | Matches |
|---------|------------|-------|---------|
| v587 (TV230) | TV208 + less mining (< 15) | 13.95 | 17m |
| v590 (TV232) | TV228 + TV230 | 13.88 | 24m |
| v595 (TV236) | TV191 + less mining | 14.25 | 23m |
| v597 (TV238) | TV208 + even less mining (< 10) | 14.76 | 9m |

Alone on TV208, less idle mining hurts. On TV191 base, marginal. The
very aggressive version (min_res < 10) shows 14.76 but only 9 matches.

## What Failed This Session

- **Wider stag explore (TV229, v586 = 10.84)**: Extending explore offsets
  to distance 32 was catastrophic. Agents waste too much time traveling
  to distant positions. The standard distance 22 is optimal.
- **30% stag scramble (TV231, v588 = 12.96)**: Reducing scramble from
  50% to 30% hurts. Scrambling creates junction turnover that helps both
  teams (cooperative scoring).
- **Combined TV191 changes (TV237, v596 = 13.87)**: Combining early aligner
  + less idle mining on TV191 hurt. The changes aren't additive — they
  interact negatively, probably because less mining + more aligners
  depletes resources.

## Top Session Variants (24m+ data)

| Rank | Version | TV# | Base | Changes | Score | Matches |
|------|---------|-----|------|---------|-------|---------|
| 1 | v594 | TV235 | TV191 | Early aligner | 14.90 | 23m |
| 2 | v592 | TV234 | TV208 | Early aligner + decay peak | 14.82 | 24m |
| 4 | v591 | TV233 | TV208 | Decay peak | 14.72 | 24m |
| 7 | v585 | TV228 | TV208 | Early aligner | 14.63 | 24m |
| prev#1 | v547 | TV191 | TV186 | 4a min_res 15 | 14.69 | 81m |

## What to Try Next

1. **TV191 + decaying peak**: Combine the #1 base with the successful
   stagnation fix (TV233). This hasn't been tried yet.
2. **Monitor v594/v592**: Need 40+ matches for reliable scores.
3. **Study why v596 (combined) failed**: The interaction between early
   aligner and less mining on TV191 base needs investigation.
4. **Consider LLM cyborg on TV235 base**: Runtime adaptation could
   break through the ~15 ceiling.
