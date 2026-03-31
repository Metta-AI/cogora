# Session Summary — 2026-03-31-062303

## Goal
Improve competition scores (was avg ~1.33 for v909/v910).

## Key Actions
1. Analyzed v909 competition match logs — found late-game junction collapse
2. Discovered competition resources are much scarcer than local (50 vs 1500)
3. Found tournament policy was missing critical improvements from local policy
4. Fixed resource thresholds, team-size cap, aligner behavior for tournament
5. Uploaded v911 (LLM), v912 (heuristic), v913 (LLM + improved aligner)

## Results
- **v912 competition avg: 1.93** (vs v909/v910 avg 1.33) — **45% improvement**
- Best single match: 5.32 (4v4 vs slanky, up from 1.06)
- Best 6v2 match: 4.34 (vs random-assay, up from 1.30)
- 2v6 matchups remain hard (0.25-0.28)
- v913 still in qualifying (LLM-based, slower)

## What Worked
- Lower resource thresholds for competition (min_res >= 5 vs 14)
- Team-size miner cap (ensures 2 miners in tournament)
- Improved aligner with hotspot patrol and expansion
- Aggressive mining stall detection (20/30/50 thresholds)

## What Didn't Work
- V2 with earlier scramblers (step 1000 vs 3000) — regressed in self-play
- Self-play testing unreliable due to map RNG and mirrored opponents

## Still TODO
- Check v913 competition results when qualifying finishes
- 2v6 matchups need fundamental improvement
- Late-game resource collapse still structural (silicon depletion)
- RL training remains the highest-priority long-term investment
