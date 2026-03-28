# Session 2026-03-28-130457 Summary

**Status**: Interrupted (container crash)

## Key Activities
- Local baseline avg=5.14 at 5k steps, avg=7.09 at 10k steps
- Uploaded v201-v207 for A/B testing various variants
- Tournament: v201-v204 all settle at 1.8-2.1, v65 still #1 at 3.59
- Discovered team-relative roles NOT the issue; gap likely in base class changes since v65
- Created AlphaV65OriginalPolicy (v202) to replicate v65 behavior
- Pickup test (PvP vs starter, 4v4): Lost badly — 0 friendly junctions
- ROOT CAUSE found: 4-agent budget too aggressive, 1 miner can't sustain economy
- Started implementing economy-first budgets (delayed aligners/scramblers)

## Key Insights
- v65 frozen with OLD base class (pre-station-fix, pre-role-fix)
- v200 stable at 2.38 (#62) — still far behind v65's 3.59
- Economy-first approach: delay aligners until min_res>=7, scramblers until step 500+ with min_res>=14
