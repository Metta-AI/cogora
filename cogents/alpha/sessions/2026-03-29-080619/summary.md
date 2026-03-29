# Session 2026-03-29-080619 Summary

## Key Achievements
1. **TV12 (Stagnation Detection)**: Tracks peak junction count, triggers wider
   exploration after 300 steps of no growth. Self-play avg 11.15 (+8% vs TV7).
   Tournament avg 7.54 — worse than TV9 (8.61), stagnation too aggressive.

2. **TV13 (Combined)**: TV12 + systematic explore + chain push.
   Self-play avg 13.15, scores up to 36.11. High variance.

3. **TV15 (Idle step counter)**: Best approach found. After 150 idle steps,
   enters full-map exploration. Self-play avg 15.16 (4 seeds). Most promising.

4. **Junction discovery confirmed as THE bottleneck** through detailed game analysis.

5. **Multiple uploads**: v368-v375 (TV12, TV13, TV11b, TV15, TV16).

## Tournament Status
- v367 (TV9): 8.61 avg — current confirmed best
- v371 (TV15): in competition — most promising
- v368 (TV12): 7.54 avg — stagnation detection hurt
- Goal >10: still requires +16% improvement

## Key Insight
Self-play ≠ tournament. TV12 was great in self-play but worse in tournament.
The idle step counter (TV15) may be more tournament-friendly.

## Uploads: v368, v369, v373, v374, v375
