# Todos

- [ ] Achieve score > 10 in CogsVsClips (current competitive ceiling: ~2.5 with heuristics)
- [ ] **Try LLM-enhanced policy (AnthropicCyborgPolicy) for tournament** — heuristic ceiling proven at ~2.5
- [ ] **Test clips mode** — other worker found VT avg 3.30 vs V4 avg 1.49 in PvP
- [ ] Investigate v216 (vanilla base) at 2.55 — simplicity beats complexity in tournament
- [ ] Fix wipe bug (~7% seeds) — HP drops to 0 near hub, not fixable in policy
- [ ] Try radically different strategies (all-scrambler rush, economic dominance, LLM adaptation)
- [x] SOLVED: v65 gap is from early opponent pool, NOT code quality (v215 pure v65 = 2.22)
- [x] CONFIRMED: all versions converge to 2.0-2.5 against current opponents
- [x] CONFIRMED: vanilla base outperforms customized policies (less is more)
- [x] Re-alignment boost (hotspot flip) — +14% local, neutral in tournament
- [x] Idle-aligner-mine — +89% local, neutral in tournament
- [x] Expand-toward-junction — helps locally, neutral in tournament
- [x] Station targeting fix, team-relative roles, stable budgets
- [x] Original v65 constants (priorities, budgets) don't help — same tournament performance
