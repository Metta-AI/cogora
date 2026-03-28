# Session Summary — 2026-03-28-061412

## Key Achievement
Found and fixed a CRITICAL bug in tournament role assignment: agents used global IDs
for role priorities, causing terrible allocation when teams had non-standard agent IDs
(e.g., team with IDs 0,1,2 had all agents become aligners; team with only ID 3 became
pure scrambler). Fix: team-relative role assignment using shared_team_ids.

## Tournament Status
- v65 still #1 at 3.24 (321 matches)
- Best recent uploads: v158/v156/v160 at 2.36
- New uploads with fix: v179 (StableBoost), v180 (Base), v181 (ZoneBoost)
- All awaiting tournament results

## Uploads This Session
v162-v168, v177-v181 (14 variants uploaded)
