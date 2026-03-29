# Todos

- [ ] Achieve score > 10 in tournament (current best: 8.69, v368/TV12)
- [ ] **Monitor v379-v381 (TV19) tournament results** — one-explorer, +7% self-play
- [ ] **Monitor v382-v384 (TV20/TV12fix) tournament results**
- [ ] **Improve 2-agent performance** — significant drag on average
- [ ] **Study top opponent strategies** — gtlm-reactive, Paz-Bot, slanky
- [ ] **Try faster initial alignment** — earlier ramp without economy damage
- [ ] **Better targeting** — improve junction selection algorithm
- [x] TV19 (one-explorer): avg 13.49 at 10K self-play, +7% over TV9 at 5K
- [x] TV19 design: agent 0 uses wide explore offsets (r15-r38) when idle, team >= 5
- [x] All-agent exploration (TV15) hurts defense on well-mapped maps (-52%)
- [x] Silicon priority override causes wipeouts — avoid _macro_directive override
- [x] v368 (TV12) is #1 at 8.69 (96 matches)
- [x] Budget changes ALWAYS hurt tournament (v371=6.71, v372=6.59 vs v368=8.69)
- [x] Chain push is neutral (TV11: avg 6.34 ≈ TV9: 6.31)
- [x] Self-play ≠ tournament (12.87 vs 8.69 = 32% gap)
- [x] Tournament uses num_agents=8 but each player controls 4
- [x] TV12 stagnation detection is best tournament innovation (+0.12 over TV9)
