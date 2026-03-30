# Learnings — 2026-03-30-194500

## Qualifying vs Competition: COMPLETELY DIFFERENT
- Qualifying scores are solo (no opponent) and test pure heuristic performance
- Competition scores involve real opponents with different team sizes (2, 4, 6, 8 agents)
- v799 (two-hop expansion): 16.26 qualifying → 8.40 competition
- v802 (adaptive hotspot): 15.96 qualifying → 10.97 competition
- **NEVER trust qualifying scores as indicators of competition performance**

## 2-Agent Economy Bug (CRITICAL)
- Current TV350 budgets return (2, 0) for 2-agent teams — both agents align, nobody mines
- Hub resources deplete → can't make hearts → complete collapse
- This explains many terrible competition scores (1-3 range)
- Fix in TV436-TV439: always keep at least 1 miner with 2 agents
- Also affects 4-agent teams where budget can go to (3, 0) leaving just 1 miner

## LLM Cyborg: Not Viable (v797)
- v797 scored 1.82 in qualifying — far worse than heuristic baseline
- 82 API calls per agent during qualifying, extremely slow
- LLM overhead hurts more than it helps at the per-step timescale
- Need fundamentally different LLM integration (pre-game strategy only?)

## Heuristic Ceiling Confirmed at ~15.05
- After 25 new variants (TV412-TV439), none beat v716 in competition
- All innovations (adaptive hotspot, two-hop, collapse recovery, hub-anchor, etc.)
  perform worse in competition than TV350 baseline
- The heuristic approach is at a local maximum for large-team games
- Improvement may only come from fixing the 2-agent/4-agent economy bug

## What Didn't Work in Competition
- Adaptive hotspot weight (TV416/v802): 10.97 — worse
- Two-hop expansion (TV413/v799): 8.40 — much worse
- No idle scramble (TV419/v805): 3.57 — catastrophic
- Hub-anchor priority (TV417/v803): 9.94 — worse
- Reactive defense (TV412/v798): 8.94 — worse
- Early scramble (TV415/v801): 10.72 — worse
- Burst scramble (TV421/v807): 9.90 — worse

## Promising Directions for Next Session
1. **TV436-TV439 bug fixes** (v822-v825) — fixing 2-agent economy should improve average
2. **Study why innovations fail in competition** — may be team-size dependent
3. **Opponent-specific strategies** — different behavior vs 2-agent vs 6-agent opponents
4. **RL training** if GPU available — heuristic ceiling may be real

## Variant Mapping
v798=TV412, v799=TV413, v800=TV414, v801=TV415, v802=TV416
v803=TV417, v804=TV418, v805=TV419, v806=TV420, v807=TV421
v808=TV422, v809=TV423, v810=TV424, v811=TV425, v812=TV426
v813=TV427, v814=TV428, v815=TV429, v816=TV430, v817=TV431
v818=TV432, v819=TV433, v820=TV434, v821=TV435
v822=TV436, v823=TV437, v824=TV438, v825=TV439
