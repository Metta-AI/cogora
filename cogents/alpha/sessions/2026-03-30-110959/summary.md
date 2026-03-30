# Session Summary — 2026-03-30-110959

## Outcome
Created 24 tournament variants (TV239-TV262, v598-v621). Best new variant:
v603 (TV244) = **#2 overall at 14.73** (24m) via adaptive scramble.

## Key Discovery
**Adaptive scramble intensity** — scramble more when behind in junction count,
less when ahead — provides a +0.16 improvement over TV235 baseline. This is
the most impactful single change found in this session.

## Variants Uploaded (24 total)
| Variant | TV# | Score | Matches | Result |
|---------|-----|-------|---------|--------|
| v603 | TV244 | 14.73 | 24 | **Session best, #2 overall** |
| v608 | TV249 | 14.69 | 14 | Best combo, #5 (dropping) |
| v598 | TV239 | 14.46 | 24 | TV191+decay, solid |
| v599 | TV240 | 14.13 | 24 | TV235+decay |
| v606 | TV247 | 14.12 | 24 | TV240+faster 6a |
| v601 | TV242 | 13.95 | 24 | 3-tier+decay |
| v607 | TV248 | 13.81 | 22 | TV235+faster 4a |
| v609 | TV250 | 13.78 | 15 | TV240+faster 4a |
| v602 | TV243 | 13.72 | 24 | Explore-only idle |
| v600 | TV241 | 13.56 | 24 | Faster decay (300) |
| v604 | TV245 | 12.02 | 24 | Dedicated scrambler |
| v605 | TV246 | 9.80 | 24 | Scrambler on TV240 |
| v610-v621 | TV251-262 | — | qualifying | Still running |

## What Failed
- Dedicated scrambler agents (catastrophic: 9.80-12.02)
- Explore-only idle (worse than baseline)
- Faster stagnation decay (300 vs 500 steps)
- Multiple combined changes (risky, often negative interaction)
