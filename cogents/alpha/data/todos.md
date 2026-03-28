# Todos

- [ ] Achieve score > 10 in CogsVsClips (current best: v65 at 3.24)
- [ ] **Understand v65's tournament advantage** — base policy scores 3.24 in tournament vs 2.0-2.6 for newer versions
- [ ] Find tournament-relevant test methodology (local self-play doesn't predict tournament)
- [ ] Consider reverting to base policy with minimal, targeted changes
- [ ] Fix wipeout recovery (10-20% wipeout rate costs ~0.7 on avg score)
- [ ] Monitor v143 (base policy reupload) tournament results
- [ ] Investigate if tournament dynamics favor simpler/more defensive play
- [ ] Try opponent simulation testing (play against own older versions)
- [x] Hotspot avoidance (ship zone detection) — implemented in v137+
- [x] A/B test base vs alpha: confirmed local ≠ tournament performance
- [x] Network-distance targeting (replaced hub-penalty)
- [x] Extensive testing framework (scrimmage, multi-seed)
- [x] Fix critical role priority bug (4-agent mode)
- [x] Upload v134-v143 to tournament
