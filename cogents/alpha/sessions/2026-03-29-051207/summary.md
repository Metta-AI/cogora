# Session 2026-03-29-051207

## Summary
Tested 7 policy variants to break past 7.5 tournament ceiling. All performed
worse than or equal to TV2 baseline in self-play. Key discovery: scoring is
cooperative (both Cogs teams share same score), suggesting we should only
scramble Clips junctions, not opponent Cogs. Uploaded v353-v358 to tournament.

## Results
- Tournament stable at ~7.5 (v348=7.57, v351=7.49, v352=7.50)
- Self-play map variance: 1.28-4.33 across seeds (dominant factor)
- CoopV2 (v358): +14% total Cogs junctions vs TV2 in self-play
- All other variants worse than TV2 baseline

## Uploads
v353 (Capture), v354 (TV2 heuristic), v355 (TV5), v356 (MaxPressure4a),
v357 (AdaptiveMap), v358 (CoopV2). All in qualifying.
