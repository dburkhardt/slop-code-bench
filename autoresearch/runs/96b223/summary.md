# Run 96b223 Summary

## Current state
- **Best single run:** 0.791 (iter 11 rep 1, no LOC guard)
- **Best with LOC guard:** 0.714 (iter 14 rep 2)
- **Mean composite (guarded, 2 runs):** 0.701
- **Mean composite (unguarded, 4 runs):** 0.718 (range: 0.645-0.791)
- **Baseline:** 0.343
- **Improvement:** 2.0-2.3x over baseline
- **Current config:** 1 review cycle, 20 turns/batch, text-only reviewer (max-turns=1, 20K context), anti-rewrite coder prompt, recursive LOC explosion guard
- **Iterations completed:** 16 (0-15 + final cross-validation)
- **Total spend:** ~$183 / $750 budget
- **Status:** Paused, can continue

## Cross-validation results (dag_execution)
| Config | file_backup composite | dag_execution composite |
|--------|----------------------|------------------------|
| Baseline (claude_code) | 0.343 | 0.140 |
| Iter 2 (1 cycle) | 0.730 | 0.248 |
| Iter 7 (20 turns) | — | 0.255 |
| Iter 16 (final config) | 0.701* | 0.246 |

*Mean of guarded runs. Improvements transfer consistently to dag_execution.

## Key results table (file_backup)
| Iter | Composite | Pass | Erosion | LOC explosion? | Key change |
|------|-----------|------|---------|----------------|------------|
| baseline | 0.343 | 0.572 | 0.707 | N/A | single-agent claude_code |
| 0 | 0.690 | 0.879 | 0.622 | No | unmodified reviewer_coder (3 cycles) |
| 2 | 0.730 | 0.911 | 0.556 | No | 1 review cycle |
| 5 | 0.739 | 0.859 | 0.383 | Yes | text-only reviewer |
| **6** | **0.765** | **0.923** | **0.511** | **No** | **20 turns/batch, anti-rewrite** |
| 11a | **0.791** | 0.879 | 0.248 | No | best single run |
| 11b | 0.645 | 0.795 | 0.496 | Yes | worst single run |
| 14a | 0.688 | 0.964 | 0.863 | No (guard) | with LOC guard |
| 14b | 0.714 | 0.917 | 0.676 | No (guard) | with LOC guard |

## Top findings (ranked by impact)
1. **Multi-batch structure** is the primary driver (+0.347 composite, baseline->iter 0)
2. **Reducing review cycles** from 3 to 1 improves results (+0.040, iter 0->iter 2)
3. **Text-only reviewer** with context injection works reliably (+0.009, iter 2->iter 5)
4. **Anti-rewrite coder instruction** + 20 turns/batch is the best config (+0.026, iter 5->iter 6)
5. **LOC explosion guard** (recursive snapshot+revert) eliminates explosions, making results more predictable
6. **LOC explosions** (~50% of unguarded runs) are the primary source of variance, driven by the coder creating package structures in subdirectories

## Dead ends
- Planning phase, 3 review cycles, 30 turns/batch, reviewer max-turns=3
- Complexity-focused reviewer prompt (broke pass rate)
- LOC count injection in coder prompt (ignored by coder)
- Non-recursive file operations (missed subdirectory files)
