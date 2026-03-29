# Todos

- [ ] Achieve score > 10 in tournament (current best: ~8.6, v367/TV9)
- [ ] **Monitor v371/v374 (TV15) tournament results** — idle explore trigger, best self-play
- [ ] **Monitor v372/v375 (TV16) tournament results** — economy fix for tournament
- [ ] **Combine TV15 idle-explore + chain push** — two orthogonal improvements
- [ ] **Improve 2-agent performance** — biggest drag on average (6-7 avg)
- [ ] **Study opponent strategies** — slanky, gtlm-reactive, Paz-Bot, coglet-v0
- [ ] **Try progressive exploration** — widen explore radius over time, not all at once
- [x] v368 (TV12) tournament avg 7.54 — stagnation detection hurt tournament
- [x] TV15 self-play avg 15.16 (4 seeds, 8a, 10K) — best policy found
- [x] Junction discovery confirmed as primary bottleneck (21/65 at step 1000)
- [x] Silicon structural bottleneck (45 extractors vs 50-58 others)
- [x] Self-play ≠ tournament (TV12: 9.9 self-play, 7.5 tournament)
- [x] Idle step counting > junction count stagnation for explore trigger
- [x] Chain push adds +~10% after frontier alignments
- [x] More scramblers crash economy (TV10 at 3.55)
- [x] Explore-always loses to Clips (no scramble pressure)
