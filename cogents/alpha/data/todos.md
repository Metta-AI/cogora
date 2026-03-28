# Todos

- [ ] Achieve score > 10 in CogsVsClips (structural ceiling ~2.75 in tournament)
- [ ] **Investigate why v17-v38 (2.75+) outperform new versions (2.1-2.4)** — same game,
  different opponent pool/era. Need 50-100+ matches for fair comparison.
- [ ] **Wait for v241-v249 to converge** — v241 at 2.35 (23m), could still rise to 2.5+.
- [ ] **Improve V65TrueReplica incrementally**: add idle-mine (NOT idle-explore!),
  re-alignment boost, resource bias. Test each feature separately with old deps.
- [ ] **Improve 2-agent performance** — currently wipes (0.00). Tournament uses 6v2/2v6.
  Better 2-agent strategy could raise overall average by 0.1-0.2.
- [ ] **Consider trained RL agent** — heuristic ceiling ~2.75, target >10. Gap of ~4x.
- [ ] Fix wipe bug (~7% seeds) — HP drops to 0 near hub, not fixable in policy
- [x] CONFIRMED: idle-mine >> idle-explore for AlphaCyborg (avg 8.05 vs 3.54 at 10k)
- [x] TESTED: Old deps (cogames 0.19) — marginal +0.2-0.3 tournament advantage
- [x] TESTED: Radical strategies (FlashRush, EconDominance, ScrambleDominance) — ALL failed
- [x] CONFIRMED: Game is reproducible (seed-dependent, ±3 variance)
- [x] CONFIRMED: Tournament ceiling ~2.75-2.81 for well-converged policies (v17/v38)
- [x] CONFIRMED: v65 gap from different era/opponent pool, NOT code quality
- [x] CONFIRMED: all heuristic versions converge to 2.0-2.4 with 20+ matches
- [x] LLM-enhanced (v225) at 2.26 — marginal +0.1 above heuristic ceiling
- [x] Survival code (hub_camp_heal) HELPS tournament — don't bypass
