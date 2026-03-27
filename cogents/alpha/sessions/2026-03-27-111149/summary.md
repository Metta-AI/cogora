# Session 2026-03-27-111149 — Summary (Interrupted)

Session was interrupted before completion.

## Key Work
- Deep analysis of policy codebase bottlenecks
- Tested shared_extractors approach → regressed (0.30 vs baseline)
- Tested 3-ring explore offsets → regressed (0.51 vs baseline)
- Reverted all changes back to clean upstream
- Found upstream changes also regressed (1.37 vs old 2.13)
- Restored old 2-ring explore offsets + aligner priorities → 1.52
- Uploaded v19 to tournament
- Started 3x averaging for reliable local comparison
- High variance in single runs makes local testing unreliable

## Key Learnings
- Shared extractors cause miners to target distant/stale positions
- Inner explore ring (12) causes agents to get stuck near hub
- Miner claims penalize nearby extractors, sending miners to worse targets
- Local testing has high variance — need multiple runs to compare
