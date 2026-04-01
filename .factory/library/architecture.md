# Architecture

How the SCBench Research Lab system works.

## System Overview

The research lab is layered on top of the upstream slop-code-bench harness. All custom code lives under `research/`. The harness provides Docker-isolated execution, evaluation, and metrics. Gas Town provides multi-agent orchestration. Dolt provides versioned experiment data storage.

## Components

### slop-code-bench (upstream, read-only)
- `src/slop_code/` - Core library: CLI, execution engine, evaluation, metrics
- `configs/` - Agent, model, prompt, environment, provider configs
- `problems/` - Benchmark problems (20 problems, 93 checkpoints)
- `tests/` - pytest suite
- Entry point: `slop-code` CLI (Typer)

### research/ (our additions)
- `research/runner/two_agent_runner.py` - Two-agent runner wrapping slop-code
- `research/prompts/` - Custom Jinja templates for implementer/reviewer
- `research/formulas/` - Gas Town experiment formula TOML
- `research/analysis/` - Analysis scripts and final report
- `research/spec.md` - Architecture specification

### Gas Town (~/gt)
- Town workspace at ~/gt with scbench rig
- Dolt databases at ~/gt/.dolt-data/ (hq and scbench)
- Mayor coordinates the research loop
- Polecats execute experiments
- Analytical roles: Idea Factory, Review Board, Red Team

## Role Asset Persistence

Role runtime files under `~/gt/scbench/polecats/<role>/.claude/` are live
workspace artifacts and are not a reliable source-controlled location. Keep a
mirrored canonical copy in-repo at `research/roles/<role>/` and sync both
locations when role instructions change.

## Data Flow

```
Idea Factory -> Hypothesis bead -> Mayor batches experiments
                                         |
                                    Red Team gate (blocks dependency)
                                         |
                                    Convoy dispatch
                                         |
                              Polecat executes formula:
                              1. Preflight canary
                              2. Implement hypothesis
                              3. Peer review (manipulation check)
                              4. Run baseline + two-agent
                              5. Validate results
                              6. Write to Dolt
                                         |
                              Review Board analyzes (validated only)
                                         |
                              Red Team post-mortem (advisory)
                                         |
                              Mayor updates strategy, loops
```

## Key Integration Points

1. **slop-code CLI <-> two-agent runner**: Runner wraps `slop-code run` for both baseline and two-agent arms. Output directories must be eval-compatible.

2. **Claude Code CLI <-> Docker**: slop-code spawns Docker containers running Claude Code for agent execution. Console billing handles API costs.

3. **NVIDIA inference <-> litellm**: For custom components (reviewer in two-agent runner, analysis), NVIDIA's OpenAI-compatible endpoint at inference-api.nvidia.com is available via NVIDIA_INFERENCE_KEY.

4. **Gas Town <-> Dolt**: Beads database uses Dolt for persistence. Experiment results and budget tracking are separate Dolt tables.

5. **Gas Town <-> Claude Code**: Polecats are Claude Code instances with role beads providing context. Mayor is also a Claude Code instance.

## Invariants

- All custom work stays under research/ - no upstream harness modifications
- Budget has two enforcement layers: Mayor Dolt check + harness per-experiment cap
- Review Board filters analytical queries on manipulation_check='passed' AND results_valid=true, with one permitted unfiltered exclusion-count query used to compute valid vs excluded totals
- Red Team gate is mechanical (blocks dependency), not advisory
- Experiment outputs must be compatible with `slop-code eval`
- Every experiment traces back to a hypothesis bead
