# Learnings — Session 2026-03-30-161800

## Key Findings

1. **v716 (TV350, hotspot=-10) = NEW #1 at 15.05** — 20 matches, stable but early.
   - Hotspot weight -10 (between -8 and -12) is optimal for re-align targeting
   
2. **v711 (TV349, no idle scramble) = #2 at 14.96** — 20 matches
   - Removing idle-time scrambling saves hearts for alignment

3. **Local scores DON'T predict tournament performance**
   - TV365 (network_weight=1.0) = 8.78 locally (+86%) but only 9.76 in tournament
   - TV346 (fast stagnation) = 7.23 locally (+26%) but only 14.42 in tournament
   - Dense network strategy fails against real opponents

4. **Combining top innovations doesn't stack**
   - TV381 (#1 + #2 combined) scored ~10 — worse than either alone
   - TV376-380 (density+stag) all scored < 13

5. **All opponents far below**: slanky=6.67, Paz-Bot=6.62, coglet=6.23

## Strategy Insights

- The heuristic ceiling is real at ~15.05 with current approach
- Parameter tuning around the sweet spot has diminishing returns
- Next breakthrough likely needs fundamentally different approach (LLM cyborg?)
- 4a budget changes (3a@60, step200, min_res 10) all harmful in tournament
- Wider scramble windows harmful
- Faster peak decay doesn't help in tournament
