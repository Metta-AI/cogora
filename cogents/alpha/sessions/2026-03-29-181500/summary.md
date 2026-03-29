# Session 2026-03-29-181500 — v442 (TV81) New #1 at 13.52

## Key Results
- **v442 (TV81) = 13.52 avg (11 matches) — new tournament leader**
- TV81 = TV79 (bridge-aware scramble) + TV70 (2-agent improvement)
- Created and uploaded TV76-TV81 (v437-v442), 6 new variants
- TV81 beats TV61's 12.83 by +0.69 points (~5.4% improvement)

## Uploads
| Version | Variant | Qualifying | Competition Avg | Matches | Key Change |
|---------|---------|-----------|----------------|---------|------------|
| v437 | TV76 | 14.11 | 12.06 | 10 | Chain-value targeting + smart expand |
| v438 | TV77 | 9.91 | ~12.0 | 1 | TV76 + adaptive scramble (worse) |
| v439 | TV78 | 14.11 | 11.17 | 3 | TV61 + chain-value expand only |
| v440 | TV79 | 8.99 | 12.29 | 12 | Bridge-aware scramble targeting |
| v441 | TV80 | 11.08 | — | 0 | Dynamic stagnation exit |
| v442 | TV81 | — | **13.52** | 11 | TV79 + TV70 (bridge scramble + 2-agent) |

## Novel Strategies Introduced
1. **Chain-value expansion**: BFS over junction graph to score transitive reachability
2. **Bridge-aware scramble**: Prioritize scrambling enemy junctions that unlock new junction clusters
3. **Adaptive scramble ratio**: Adjust scramble % based on junction health (didn't work)
4. **Dynamic stagnation exit**: Reduce scramble when losing junctions (marginal)

## Conclusion
Bridge-aware scramble targeting is the breakthrough. It turns defensive scrambling into
network expansion, preferring enemy junctions that bridge to unreachable neutral clusters.
Combined with 2-agent improvement, TV81 leads the tournament. Further work should focus
on refining bridge scoring weights and reducing the 35% overhead (retreat/heal time).
