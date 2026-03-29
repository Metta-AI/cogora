# Session 2026-03-29-010815 Summary

## Goal
Score >10 in CogsVsClips tournament. Current best: v290 at 6.84 avg.

## Key Results
- Created 10 new policy variants (Ultra, V2-V5, Coop, EconMax, TeamFix, Focused, SustainV2)
- UltraV3 scored **11.47 locally** (8a) — 3x improvement over Aggressive
- But UltraV3 scored **~1.0 in tournament** — chain expansion hurts tournament
- Discovered tournament scoring is cooperative (both teams same score)
- Discovered num_agents bug (total vs per-team)
- Tournament environment changed: v324 (Aggressive) scores 2.75 in 6a vs v290's 7.78

## Policies Uploaded
v319=Ultra, v320=UltraV2, v321=UltraV3, v322=UltraV4, v323=UltraV5,
v324=Aggressive, v325=Coop, v326=EconMax, v327=TeamFix, v331=Focused, v332=SustainV2

## Status
- Tournament environment changed — scores much lower across the board
- v327 (TeamFix) results pending
- v331 (Focused), v332 (SustainV2) results pending
- Need to investigate tournament environment changes
