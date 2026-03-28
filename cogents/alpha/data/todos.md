# Todos

- [ ] Achieve score > 10 in CogsVsClips (heuristic ceiling ~2.15, LLM ceiling ~2.3)
- [ ] **Amplify LLM integration** — v225 (LLM) scored 2.26 vs heuristic 2.15.
  v230 uploaded with actual LLM directive usage (not just logging).
  Need more aggressive LLM strategy: real-time adaptation, opponent analysis.
- [ ] **Investigate game engine regression** — v60-v65 era scored 2.89-3.59 on older
  mettagrid version. Current 0.21.1 caps at 2.15-2.26. May need to adapt to changes.
- [ ] **Consider trained RL agent** — heuristic+LLM ceiling is ~2.3, target is >10.
  Gap of 4x suggests trained agents needed (as game designers intended).
- [ ] **Monitor v228 tournament results** — AlphaTournamentPolicy with idle-explore
  Clips PvP avg 3.97 (best 10.29), but tournament may differ
- [ ] Fix wipe bug (~7-25% seeds) — map-dependent, agents die before establishing territory.
  hub_camp_heal HELPS in tournament (survival code is beneficial).
- [x] LLM-enhanced policy tested — v225 at 2.26 vs heuristic 2.15. Small but real advantage.
- [x] AlphaCyborg (v224) best heuristic — settled at 2.08 with 24 matches.
- [x] Survival code bypass HURTS tournament (v222 at 1.61). Don't skip hub_camp_heal.
- [x] Clips PvP: AlphaCyborg avg 7.46 at 10k (seed 5 = 14.17). Strong locally.
- [x] idle-mine causes gear churn — switched to idle-explore in AlphaTournamentPolicy
- [x] AlphaTournamentPolicy clips avg 3.97 (10 seeds), best 10.29
- [x] V4 (AlphaCyborgPolicy) overfits to self-play — much worse in PvP clips mode
- [x] Hotspot flip helps locally (+89%) but gear churn in PvP negates benefit
- [x] 2-agent games = hard loss (0.00-0.15). Economy can't sustain with 2 agents.
- [x] SOLVED: v65 gap is from early opponent pool + older game engine version.
- [x] CONFIRMED: all heuristic versions converge to 2.0-2.2 with 20+ matches.
