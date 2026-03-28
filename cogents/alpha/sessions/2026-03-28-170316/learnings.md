# Learnings: Session 2026-03-28-170316

## Policy Comparison (Definitive Results)

### 4-agent 10k clips (5 seeds)
- AlphaCyborg: avg 3.24 (3.96, 0.90, 0.96, 1.84, 8.54)
- SmallTeam: avg 0.88 (0.00, 0.62, 0.54, 1.75, 1.50)
- Expander: avg 2.11 (2.65, 2.23, 1.97, 1.63, 2.05)

### 8-agent 5k clips (10 seeds)
- AlphaCyborg: avg 4.34 (0.00, 4.11, 4.21, 5.43, 8.29, 5.75, 3.34, 6.20, 4.48, 1.54)
- Expander: avg 3.89 (7.47, 1.57, 0.00, 4.48, 7.38, 8.14, 2.97, 6.00, 0.00, 0.87)

### Key Findings
1. **AlphaCyborg is the best heuristic** across both team sizes
2. **SmallTeam's aggressive early alignment hurts economy** — economy-first is correct
3. **Tighter retreat margins cause more wipes** (Aggressive avg 3.09 at 8-agent)
4. **Expander expansion helps on some maps but hurts average** — wider exploration wastes time
5. **Non-determinism exists**: same seed ± ~10% score, ~10-15% wipe rate inherent

## RL Training Insights
- CPU LSTM training: 18.8M steps, 200 epochs in ~40 min at 10K SPS initially
- SPS degrades as training progresses (1.2K at 18.8M steps, making 50M infeasible)
- At 200 epochs: RL mines resources (carbon/germanium/oxygen/silicon) but zero alignment
- Checkpoint available at /tmp/cogames/train_4agent/177471761539/model_000200.pt
- Need 1000+ epochs for scoring behavior — requires GPU

## Tournament Structure (Confirmed)
- 75% 4-agent games (2v2, 1v3, 3v1 splits)
- 25% 8-agent games
- Multiple opponents: slanky, gtlm-reactive, coglet-v0
- Matches take 10-30 minutes to complete

## What Didn't Work
- AlphaSmallTeamPolicy: Aggressive alignment from step 0 doesn't help; economy-first is essential
- AlphaAggressivePolicy: Tighter retreat margin (12 vs 15) causes more deaths
- AlphaExpanderPolicy: Wider expansion range (50 vs 40) trades peak for consistency, net worse
- CPU RL training: Both LSTM and stateless models too slow without GPU
- AnthropicCyborgPolicy locally: API retries endlessly

## What the Data Shows
- Heuristic ceiling is structural at ~2.5-2.8 in tournament
- Local self-play scores (3-8) don't predict tournament scores (2.0-2.5)
- The gap to >10 is ~4x — not achievable by heuristic tuning alone
- RL is the only viable path to >10, but requires GPU
