# Learnings — Session 2026-03-30-212418

## Key Findings

### 1. Aligner Floor: Helps 6v2, Hurts Average
- Floor of 2-3 aligners dramatically improves 6-agent games vs strong opponents
  - v840 scored 8.99 vs modular-lstm 6v2 (was 2-5 with v716)
  - v840 scored 15.40 vs slanky 6v2
- BUT floor hurts 4v4 and 2v6 performance, dragging the average below v716 (15.05)
- The floor constrains resource recovery during economic crises

### 2. The 2-Agent Economy Death Spiral
- Root cause: budget drops to (1,0) when min_res < 7 in 2-agent games
- This creates a dedicated miner who never deposits carbon (stuck in retreat loop)
- Economy permanently dead → 0 junctions for 8000+ steps
- Fix (TV465): always (2,0) for 2-agent + relax scramble gate
- BUT: marginal improvement only (modular-lstm still destroys us)

### 3. Zero-Scrambler Bug Is Not a Bug
- TV350 (v716=15.05, #1) also has 0 scramblers — same as all TV334+ variants
- The scramble behavior comes from idle_align_scramble in the aligner action
- Adding scramblers to the budget doesn't help (TV455-461 tested)

### 4. Crisis Recovery Mode (TV447)
- When friendly_j=0 for 300+ steps, force persistent scramble of hub-proximal enemy junctions
- Helps in theory but didn't significantly improve competition scores
- The real issue: agents can't reach distant enemy junctions before running out of HP

### 5. Local Scores Don't Predict Tournament
- TV448 scored +74% locally but performed worse in competition
- Self-play scores are unreliable (same policy cancels itself)
- Only tournament results with diverse opponents matter

### 6. Heuristic Ceiling Confirmed
- v716 (TV350) at 15.05 is the heuristic ceiling
- All tuning attempts (25+ variants this session) score lower
- RL training is needed to fundamentally beat modular-lstm and slanky
- modular-lstm with just 2 agents holds 8+ junctions while our 6 hold 2

## Opponent Analysis
- **modular-lstm-bc:v13**: Strongest opponent. 2 agents hold territory better than our 6
- **slanky:v112**: Efficient. Ties us 6v2 at ~8-16 depending on variant
- **gtlm-reactive-v3**: Moderate. We score 0.18-12.85 depending on agent count
- **Paz-Bot-9005**: Weakest. We score 9-17 consistently
- **mammet:v11**: Moderate. We score 2-11 depending on agent count
- **coglet-v0:v23**: Weak. We score 1-7

## Strategic Recommendations
1. **Don't change TV350** for 5+ agents — it's optimal for the current tournament mix
2. **Focus on RL** to break the heuristic ceiling
3. **2-agent games** need fundamentally different strategy (not just budget changes)
4. **Pre-game LLM** strategy to adapt to opponent type could help but is complex
