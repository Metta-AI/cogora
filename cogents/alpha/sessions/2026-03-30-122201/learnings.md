# Learnings — 2026-03-30-122201

## v632 (TV272) = NEW #1 at 15.17 (24m)

The winning formula: TV234 base (TV208+early aligner+decaying peak) + adaptive scramble + 7 aligners at very high resources (min_res >= 150).

This combines four proven improvements:
1. **TV208 stagnation thresholds** (22/35/70) — more aggressive aligner ramp
2. **Early 3rd aligner at step 15** — faster initial expansion
3. **Decaying peak junction count** — better stagnation recovery
4. **Adaptive scramble** (150/100/50 based on junction balance) — smart scramble intensity
5. **7 aligners at min_res >= 150** — capitalize on resource surplus

## Feature Interaction Insights

**Works together:**
- TV208 thresholds + decaying peak + adaptive scramble = v623 (14.97)
- TV191 thresholds + adaptive scramble + early aligner + TV208 thresholds = v625 (14.98)
- Everything above + 7 aligners = v632 (15.17) — best of all

**Doesn't work:**
- Capture-optimized scramble: TOXIC everywhere (12.61 on TV263, 11.18 on TV264, 10.96 on TV272)
  The -50 bonus for capturable junctions causes agents to chase far-away targets
  instead of nearby opportunistic scrambles. Distance matters more than capturability.
- Skip idle scramble when ahead (v627=11.98): Opportunistic scrambling is always
  valuable — it creates neutral junctions that can be realigned, maintaining pressure.
- Earlier 4th aligner (min_res 30): Too aggressive, starves economy (v629=13.53)
- Lower thresholds 18/30/60 (v636=14.52): Also too aggressive
- Faster stag entry on TV264 (v635=13.49): Decay already handles stagnation timing
- Aggressive scramble windows 175/125/75 (v624=14.58): Too much scramble time

## Why Capture Scramble Fails

The capture-optimized targeting adds -50 score bonus for enemy junctions within
alignment range of our network. This seems smart (scramble+realign = +2 swing) but
actually hurts because:
1. Capturable junctions are near our network = near our hub = well-defended by proximity
2. The most impactful scrambles target distant junctions deep in enemy territory
3. The -50 bonus overwhelms the distance penalty, sending agents on long journeys
4. Nearest-enemy targeting works better because it minimizes travel time

## Top Variants After This Session

1. v632 (TV272) = 15.17 (24m) — **session best, new overall #1**
2. v625 (TV266) = 14.98 (24m)
3. v623 (TV264) = 14.97 (24m)
4. v628 (TV269) = 14.92 (24m)
5. v585 = 14.84 (27m) — older variant gaining with more matches
6. v592 (TV234) = 14.82 (24m) — previous #1

## What to Try Next

1. **TV272 + even more aligners**: Try 7a at min_res >= 100 (lower threshold)
2. **TV272 + lower stag_min_step**: Enter stag at step 400 instead of 500
3. **TV272 + 3-tier stagnation**: Differentiate 2a/4a/6a+ stag thresholds
4. **Study opponent match logs**: Understanding gtlm-reactive, coglet strategies
5. **LLM cyborg on TV272 base**: Runtime strategy adaptation could push past 15
