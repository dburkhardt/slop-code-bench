# H227: Structured Review Reduces Verbosity

**Hypothesis:** Structured reviewer prompts that explicitly target verbosity will reduce the verbosity slope compared to baseline.

**Bead:** sc-hypotheses.227

**Testable claim:** Structured reviewer prompts reduce verbosity slope by at least 15%.

**Predicted outcome:** Two-agent with structured review prompt yields lower verbosity slope than baseline across 3+ problems.

## Design

Two arms, run on each problem independently:

| Parameter | Baseline (single-agent) | Treatment (two-agent) |
|-----------|------------------------|-----------------------|
| Agent type | claude_code | reviewer_coder |
| Model | opus-4.5 | opus-4.5 |
| Implementer prompt | just-solve | just-solve |
| Reviewer prompt | N/A | anti-slop-reviewer.jinja |
| Budget split | N/A | 70/30 |
| Step limit | 100/checkpoint | 100/checkpoint |
| Cost limit | $5.0/checkpoint | $5.0/checkpoint |
| Thinking | none | none |

**Problems:** file_backup, etl_pipeline, database_migration

Note: the original bead specified `todo_app` as a problem, but no such problem exists in the benchmark. `etl_pipeline` and `database_migration` were substituted to reach the 3+ problem threshold required by the predicted outcome.

## Reviewer Prompt

The treatment arm uses `research/prompts/anti-slop-reviewer.jinja`, which instructs the reviewer to aggressively eliminate seven categories of slop: verbose comments, defensive bloat, unrequested features, trivial wrappers, single-use helpers, variable bloat, and abstraction theater.

This contrasts with the default reviewer (`configs/prompts/default_reviewer.jinja`), which has a broader focus on structural problems, duplication, complexity, and dead code.

## Running the Experiment

### Using experiment_pipeline.py (recommended)

Each invocation runs both the single-agent baseline and two-agent treatment on the given problem, evaluates both, and writes results to Dolt:

```bash
# file_backup
python research/runner/experiment_pipeline.py \
    --problem file_backup \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.227

# etl_pipeline
python research/runner/experiment_pipeline.py \
    --problem etl_pipeline \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.227

# database_migration
python research/runner/experiment_pipeline.py \
    --problem database_migration \
    --model opus-4.5 \
    --budget 10.0 \
    --budget-split 70 \
    --reviewer-prompt research/prompts/anti-slop-reviewer.jinja \
    --hypothesis-id sc-hypotheses.227
```

### Using run configs (via slop-code CLI)

```bash
# Baselines
python -m slop_code run --config configs/runs/h227_file_backup_baseline.yaml
python -m slop_code run --config configs/runs/h227_etl_pipeline_baseline.yaml
python -m slop_code run --config configs/runs/h227_database_migration_baseline.yaml

# Two-agent with anti-slop reviewer
python -m slop_code run --config configs/runs/h227_file_backup_anti_slop.yaml
python -m slop_code run --config configs/runs/h227_etl_pipeline_anti_slop.yaml
python -m slop_code run --config configs/runs/h227_database_migration_anti_slop.yaml
```

### Using the run script

```bash
bash research/experiments/run_h227.sh
```

## Primary Metrics

| Metric | How measured | Comparison |
|--------|------------|------------|
| Verbosity slope | Least-squares slope of per-checkpoint verbosity scores | Treatment < baseline by >= 15% |
| Verbosity (mean) | Mean of per-checkpoint verbosity_flagged_pct | Lower is better |
| Pass rate | Per-checkpoint core pass rates | Treatment should not regress |
| Cost | Total USD per arm | Report overhead |

## Confounds and Controls

- H2 experiment found that the reviewer_coder agent had a reviewer extraction bug (reviewer_suggestion_chars=0). Verify that reviewer suggestions are being extracted before interpreting results.
- N=1 per condition per problem. No variance estimation without repeated runs.
- The anti-slop reviewer prompt includes the spec, which gives the reviewer more context than the default reviewer prompt.
- Budget differences between arms may confound quality comparisons: the implementer in the two-agent arm gets only $3.50 per checkpoint vs $5.00 for the single-agent baseline.

## Verdict

_Pending experiment execution._

## Results

### file_backup

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### etl_pipeline

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

### database_migration

| Metric | Baseline | Anti-Slop Two-Agent |
|--------|----------|-------------------|
| Mean verbosity | | |
| Verbosity slope | | |
| Mean erosion | | |
| Erosion slope | | |
| Total pass rate | | |
| Total cost | | |

## Interpretation

_To be filled after experiment runs._

## Run Artifacts

_To be filled after experiment runs._
