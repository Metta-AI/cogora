# Session 2026-03-29-100801 Learnings

## Idle Stagnation Bug (Critical Discovery)
- When all nearby junctions are aligned, aligners loop on `idle_align_scramble` forever
- The 2-agent match log showed agent 6 stuck at position (-13,-15) for 5000+ steps
- Root cause: default explore offsets (radius 22) only cover ~25% of the 88x88 map
- Junctions at radius 30-40 are NEVER discovered by standard exploration

## Exploration Strategy: One Explorer Wins
- TV15 (all agents explore): +30% on under-explored maps, -52% on well-mapped maps
- TV16 (conditional explore by junction count): too conservative, barely triggers
- TV17 (wider standard offsets): minimal impact
- **TV19 (agent 0 wide explore, others standard): +7% avg, no regressions**

## Why One Explorer Works
- Losing 1/5 aligners to exploration: minor efficiency loss
- Discovery benefit: finds junctions that feed ALL aligners
- Defense preserved: 4/5 aligners still scramble and re-align
- With all agents exploring (TV15): no defense → enemy takes junctions

## Silicon Priority Is Dangerous
- Overriding `_macro_directive` with silicon priority causes seed 4 wipeout
- Hub resources are tight (12 per resource with 4 agents)
- Don't override economy heuristics without extensive multi-seed testing

## Team Size Matters
- Gate exploration on team_size >= 5
- With 4 agents, losing any aligner efficiency is too costly
- 2-agent games: TV9's approach (mine then align) is already optimal

## Self-Play ≠ Tournament (Reminder)
- Self-play has 8 same-policy agents (total cooperation)
- Tournament has 2-6 of our agents + partner's agents
- Features that work in self-play may hurt in tournament
