# Todos

- [ ] Achieve score > 10 in CogsVsClips
- [ ] Use AlphaCyborgPolicy for local testing, AnthropicCyborgPolicy for tournament
- [ ] Test AlphaCyborgPolicy locally and establish baseline scores
- [ ] Upload cyborg policy to tournament and check results
- [ ] Tune AlphaCogAgentPolicy overrides in anthropic_pilot.py (pressure budgets, retreat logic)
- [ ] Investigate bad map layouts that cause score < 2
- [ ] Try territory-aware pathfinding (cost=4 outside territory in A*)
- [ ] Optimize alignment chain building (prioritize junctions that extend network)
- [ ] Check competition match results
- [x] Switch from MettagridSemanticPolicy to cyborg policies
- [x] Fix hub camping infinite wait bug (step timeout)
- [x] Fix economy death spiral: hub camping prevents wipeout
- [x] Economy-responsive pressure budgets
- [x] Set up environment (cogames, auth, venv)
- [x] Upload to tournament (v15-v84)
