# Todos

- [ ] Achieve score > 10 in CogsVsClips (best local: 8.72 4a, 9.24 8a, avg ~5.55 4a)
- [ ] **Monitor v343 (AdaptiveTeam) tournament results** — best candidate
- [ ] **Monitor v339 (Sustainable), v342 (AdaptiveTeam v2) results**
- [ ] **Improve 4a performance** — avg 5.55 needs to reach 10+
- [ ] **Faster early alignment** — steps 0-200 have 0 junctions (wasted ticks)
- [ ] **Better network connectivity** — junction distribution causes huge variance
- [ ] **Mining efficiency** — reduce travel time, optimize deposit threshold
- [ ] **Study opponent strategies** — analyze top opponents from match logs
- [ ] **GPU-accelerated RL training** — heuristic approach may have reached ceiling
- [x] FIXED: economy collapse in 2nd half by capping budget with team_size
- [x] DISCOVERED: max_steps=10000 in tournament (was testing at 5000)
- [x] DISCOVERED: scoring is PER TEAM, not cooperative (self-play artifact)
- [x] CONFIRMED: scrambling essential (without: 2.77 vs with: 8.67)
- [x] CONFIRMED: economy sustainability is #1 factor for 10k-step games
- [x] CONFIRMED: num_agents bug helps large teams but kills economy in small teams
