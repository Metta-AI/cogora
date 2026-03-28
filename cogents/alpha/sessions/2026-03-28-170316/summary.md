# Session 2026-03-28-170316 — Interrupted

Session was interrupted during RL training and policy comparison testing.

## Key Findings
- AlphaCyborg remains best heuristic (avg 4.89 at 8-agent, 3.24 at 4-agent clips)
- AlphaAggressive worse (3.09 avg) — tighter retreat causes more wipes
- SmallTeam worse (0.88 avg at 4-agent) — aggressive alignment hurts economy
- RL training was at 17.7M steps when interrupted, agents learning hearts
- New opponents: slanky:v112, gtlm-reactive, coglet-v0:v7
- Heuristic ceiling confirmed ~3-5 for clips self-play
- v250-v254 uploaded, matches were still running
