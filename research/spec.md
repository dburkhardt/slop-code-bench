# SCBench Research Lab — Architecture Spec

A Gas Town workspace that autonomously explores whether a two-agent
(Implementer + Reviewer) system can beat single-agent baselines on
SlopCodeBench.

---

## 1. Research Question

**For a fixed compute budget, can an Implementer + Reviewer two-agent
system beat a single-agent baseline on SlopCodeBench, and what
configuration makes that work?**

Secondary questions:

- Does the two-agent advantage vary by checkpoint depth (early vs. late)?
- What's the optimal budget split between implementer and reviewer?
- Does the reviewer reduce structural erosion and verbosity?
- At what budget level does the two-agent pattern start outperforming
  single-agent?

### Constraints

- **Single harness**: Claude Code only (no cross-harness comparisons).
- **Budget-controlled**: The town operates within a total dollar ceiling,
  then stops.
- **Fully autonomous**: The human sets the budget and reviews the final
  report. Everything else is agent-driven.
- **Proof-of-concept quality**: Rigorous enough to share internally and
  recruit collaborators, but not a paper submission.

---

## 2. SlopCodeBench

SCBench evaluates coding agents under iterative specification
refinement. The agent implements a spec, then extends its own code as
the spec changes across sequential checkpoints.

Key properties: 20 problems with 93 total checkpoints; no prescribed
internal interfaces (architectural decisions are measured); no visible
test suite; two trajectory-level quality signals — **verbosity**
(redundant/duplicated code) and **structural erosion** (complexity
concentrated in high-complexity functions); tokens and cost tracked per
checkpoint; Docker-isolated execution.

Repo: `github.com/SprocketLab/slop-code-bench`.
CLI: `slop-code run`, `slop-code eval`.
Configs in `configs/agents/`, `configs/prompts/` (Jinja),
`configs/environments/`.

### Why This Benchmark

The erosion and verbosity signals are exactly what a reviewer agent
should help with. A single agent accumulates slop because it never
steps back to refactor. The reviewer is an explicit anti-slop
intervention. If we can show it flattens the erosion slope without
tanking pass rate, that's a clean result.

---

## 3. Rig Structure

The workspace is a single rig: this fork of `slop-code-bench`.

```
slop-code-bench/                 # upstream harness (untouched)
├── configs/agents/              # upstream + custom agent configs
├── configs/prompts/             # upstream + custom Jinja templates
├── configs/environments/        # upstream
├── ...                          # all other upstream directories
└── research/                    # our additions
    ├── spec.md                  # this file
    ├── runner/                  # two-agent runner script
    │   └── two_agent_runner.py  # wraps slop-code run
    ├── formulas/                # experiment formula TOML
    │   └── mol-scbench-experiment.formula.toml
    ├── prompts/                 # reviewer/implementer prompt variants
    └── analysis/                # Review Board queries, final report
```

Gas Town adds this fork as a rig:

```bash
gt rig add scbench <fork-url>
```

Polecats execute experiments within the rig but don't modify upstream
harness code. All custom work lives under `research/`.

---

## 4. Town Topology

```
┌──────────────────────────────────────────────────────┐
│  YOU (Overseer)                                      │
│  Set budget, review final report                     │
│  Otherwise hands-off                                 │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│  MAYOR (PI Agent)                                    │
│  Coordinates the research loop                       │
│  Must obtain Red Team sign-off before dispatching    │
│  Maintains research log on a persistent bead         │
└──┬──────────┬──────────────┬──────────┬──────────────┘
   │          │              │          │
   ▼          ▼              ▼          ▼
┌───────┐ ┌────────┐ ┌────────┐ ┌─────────────┐
│ Idea  │ │  Lab   │ │  Red   │ │   Review    │
│Factory│ │(Pcats) │ │  Team  │ │   Board     │
└───────┘ └────────┘ └────────┘ └─────────────┘
```

### Analytical Roles as Polecats with Role Beads

The Idea Factory, Review Board, and Red Team are **polecats with
dedicated role beads** — not crew members. This matches Gas Town's
architecture: stateless agents, stateful data. Each polecat rebuilds
context from its beads at session start.

Why not crew members: crew workspaces are persistent git clones designed
for human operators. These analytical roles don't need persistent
worktrees — they need persistent *knowledge*, which lives in beads.

Role beads for each:

| Role          | Role bead              | Session pattern                      |
|---------------|------------------------|--------------------------------------|
| Idea Factory  | `sc-idea-factory-role` | Dispatched by Mayor to generate hypotheses. Queries KB epic, searches web, files findings and hypotheses as beads. |
| Review Board  | `sc-review-board-role` | Dispatched by Mayor after experiments complete. Queries Dolt experiment table, files conclusion beads. |
| Red Team      | `sc-red-team-role`     | Dispatched by Mayor before batch dispatch (blocking) and after results (advisory). Files critique and post-mortem beads. |

---

## 5. Roles

### Mayor = Principal Investigator

Coordinates the full research loop: consult Idea Factory for
hypotheses -> plan experiments -> get Red Team review -> dispatch to
polecats -> wait for results -> send to Review Board -> read
conclusions and Red Team post-mortem -> update strategy -> loop.

Maintains a research log as notes on a persistent bead — the running
narrative of what's been tried, learned, and what's next. This log is
the persistent memory that survives across sessions.

### Idea Factory = Polecat (Theorist)

Builds a **cumulative research knowledge base** and generates
hypotheses grounded in that knowledge.

**Knowledge base.** A persistent epic (`sc-research-kb`) where every
finding — papers, blog posts, strategies, best practices — is a bead.
Labels provide taxonomy: `literature`, `strategy`, `best-practice`,
`dead-end`, `web-search`. The Idea Factory queries this via
`bd search`, `bd list --label`, and `bd list --parent` to rebuild
context each session.

**Web search.** The Idea Factory actively searches for relevant work —
multi-agent coding strategies, code review automation, anti-slop
techniques, SlopCodeBench discussions — before generating hypotheses.
Every finding is logged as a KB bead before any hypothesis is proposed.
The goal is that every session leaves the KB richer than it found it.

**Hypotheses.** Filed as beads under a separate `Hypotheses` epic.
Each hypothesis bead stores provenance in its metadata field:

```json
{
  "discovered_from": ["sc-kb-042", "sc-kb-057"],
  "testable_claim": "...",
  "predicted_outcome": "...",
  "experiment_configs": { ... }
}
```

This uses metadata JSON rather than a dependency type because
provenance is annotation, not an operational relationship. The
`discovered_from` IDs trace back to KB beads for auditability.
Queryable via Dolt JSON functions:

```sql
SELECT id, title FROM issues
WHERE JSON_EXTRACT(metadata, '$.discovered_from') IS NOT NULL;
```

### Lab = Polecats (Experimentalists)

Ephemeral polecats that execute experiments. Each polecat receives an
experiment molecule (poured from the experiment formula), implements the
hypothesis, gets peer-reviewed, runs the experiment, and writes results
to the Dolt ledger. 3-5 concurrent polecats on the Brev instance.

### Review Board = Polecat (Analyst)

Dispatched by Mayor after experiment batches complete. Queries the
experiments Dolt table. **Always** filters on
`manipulation_check = 'passed' AND results_valid = true` — never
includes unverified experiments. Identifies patterns, computes
statistical summaries, files conclusion beads. Also reports how many
experiments were excluded due to validation failures (useful signal for
systematic infra problems).

### Red Team = Polecat (Adversarial Reviewer)

Finds flaws before budget is burned and challenges interpretations
after results land. Intervenes at two points:

**Pre-dispatch (blocking).** Mayor creates a "Proposed Batch N" bead
and a Red Team review bead. The review bead **blocks** the batch bead
via a `blocks` dependency. The Mayor assigns the review bead to the
Red Team polecat. The batch bead will not appear in `bd ready` until
the Red Team closes its review bead — this is mechanical enforcement
via Gas Town's existing dependency system. The Red Team files specific,
actionable objections. The Mayor addresses each objection in writing
before the Red Team closes the review.

```bash
# Mayor creates batch + blocking review
bd create "Proposed Batch 3" --parent sc-batches
bd create "Red Team Review: Batch 3" --parent sc-reviews
bd dep add sc-rt-review-003 --blocks sc-batch-003
gt sling sc-rt-review-003 scbench   # dispatch to Red Team polecat
# Batch 003 won't appear in bd ready until review is closed
```

**Post-results (advisory).** After the Review Board analyzes results,
Red Team challenges interpretation: does the data support the
conclusion? What alternative explanations exist? Is sample size
sufficient? Files a post-mortem bead. This review is advisory — it
doesn't block, but the Mayor must read it before updating strategy.

The Red Team's role is explicitly adversarial — it does not encourage,
congratulate, or rubber-stamp. It finds problems. The Mayor and Review
Board provide the optimism; the Red Team provides the rigor.

---

## 6. The Two-Agent System Under Test

The core artifact that polecats invoke. A runner script in
`research/runner/` that wraps `slop-code run` with a two-agent pattern:

```
For each checkpoint in problem:

  1. Implementer receives spec + prior code
     -> Implements/extends the solution
     -> Budget: X% of checkpoint budget

  2. Reviewer receives spec + implementer's code
     -> Reviews for structural issues, slop, unnecessary complexity
     -> Refactors/rewrites as needed
     -> Budget: (100-X)% of checkpoint budget

  3. Record: pass rate, erosion, verbosity, tokens per agent, cost
```

Dimensions the PI should explore: budget split ratio; reviewer
instructions (anti-slop vs. architecture vs. test-writing); reviewer
access (current code only vs. full spec history); review depth (full
refactor vs. suggestions-only); checkpoint-adaptive ratios.

---

## 7. Experiment Formula

Each experiment is a molecule poured from a TOML formula. The formula
lives at `research/formulas/mol-scbench-experiment.formula.toml`.

```toml
description = """
SCBench experiment molecule. Runs a two-agent vs. single-agent
comparison on a single problem with a specific hypothesis and config.
Six phases: preflight, implement hypothesis, peer review, run
experiments, validate results, report.
"""
formula = "mol-scbench-experiment"
type = "workflow"
version = 1

[vars]
[vars.problem_id]
description = "SCBench problem ID to run"
required = true

[vars.model]
description = "Model to use (e.g., claude-sonnet-4-6)"
required = true

[vars.hypothesis_id]
description = "Bead ID of the hypothesis being tested"
required = true

[vars.hypothesis_description]
description = "Plain-text description of what this experiment tests"
required = true

[vars.implementer_prompt]
description = "Path to implementer Jinja prompt template"
default = "configs/prompts/default_implementer.jinja"

[vars.reviewer_prompt]
description = "Path to reviewer Jinja prompt template"
default = "configs/prompts/default_reviewer.jinja"

[vars.budget_split]
description = "Percentage of per-checkpoint budget for implementer (e.g., 70)"
default = "70"

[vars.total_budget_usd]
description = "Maximum spend for this experiment in USD"
required = true

[[steps]]
id = "preflight"
title = "Run preflight canary"
description = """
Run a $0.50 canary (single checkpoint, trivial problem) to validate
Docker, API keys, and the pipeline.

```bash
cd research/runner
python two_agent_runner.py --canary --budget 0.50
```

**Exit criteria:** Canary produces valid output directory with eval
results. If it fails, escalate:

```bash
gt escalate --severity high --reason "Preflight canary failed" \
  --related {{hypothesis_id}}
```

Do NOT proceed to the next step if preflight fails.
"""

[[steps]]
id = "implement-hypothesis"
title = "Implement the hypothesis"
needs = ["preflight"]
description = """
Modify the two-agent runner, prompt templates, or config to implement
whatever the hypothesis ({{hypothesis_id}}) claims to test:

> {{hypothesis_description}}

Commit with a clear message referencing the hypothesis ID:

```bash
git commit -m "experiment: implement {{hypothesis_id}} — {{hypothesis_description}}"
```

**Exit criteria:** Working tree clean, commit references hypothesis ID.
"""

[[steps]]
id = "peer-review"
title = "Peer review (manipulation check)"
needs = ["implement-hypothesis"]
description = """
A second agent reads the hypothesis description and the implementation
diff, then answers:

1. Does the code change match the hypothesis?
2. Are there unintended confounds?
3. Is the baseline still fair?
4. Could this trivially fail for mechanical reasons?

Record findings:

```bash
bd update {{hypothesis_id}} --set-metadata manipulation_check=passed
bd update {{hypothesis_id}} --notes "Manipulation check: [findings]"
```

If any check fails:

```bash
bd update {{hypothesis_id}} --set-metadata manipulation_check=failed
bd update {{hypothesis_id}} --notes "BLOCKED: [reason]"
gt escalate --severity medium --reason "Manipulation check failed for {{hypothesis_id}}"
```

**Exit criteria:** `manipulation_check` set to `passed` or `failed`.
If failed, stop — do not proceed.
"""

[[steps]]
id = "run-experiments"
title = "Run baseline + two-agent experiments"
needs = ["peer-review"]
description = """
Run both the single-agent baseline and the two-agent system:

```bash
# Baseline (single agent)
slop-code run --problem {{problem_id}} --model {{model}} \
  --budget {{total_budget_usd}}

# Two-agent
cd research/runner
python two_agent_runner.py \
  --problem {{problem_id}} \
  --model {{model}} \
  --implementer-prompt {{implementer_prompt}} \
  --reviewer-prompt {{reviewer_prompt}} \
  --budget-split {{budget_split}} \
  --budget {{total_budget_usd}}
```

The runner script enforces a per-experiment cost cap. If cumulative API
cost exceeds `{{total_budget_usd}}`, the run aborts and logs partial
results. This is the harness-level budget enforcement layer.

**Exit criteria:** Both runs complete (or abort with logged reason).
"""

[[steps]]
id = "validate-results"
title = "Validate experiment outputs"
needs = ["run-experiments"]
description = """
Verify both runs produced valid output:

- Output directories exist with expected structure
- Eval results present for each checkpoint
- No budget overruns beyond the cap
- Cost accounting matches API logs

Flag invalid experiments:

```bash
bd update {{hypothesis_id}} --set-metadata results_valid=true
# or
bd update {{hypothesis_id}} --set-metadata results_valid=false
bd update {{hypothesis_id}} --notes "INVALID: [reason]"
```

**Exit criteria:** `results_valid` set to `true` or `false`.
"""

[[steps]]
id = "report"
title = "Write results to Dolt ledger"
needs = ["validate-results"]
description = """
Insert a row into the experiments Dolt table with all metrics. Update
the budget table with actual spend.

```sql
INSERT INTO experiments (
  problem_id, model, mode, hypothesis_id,
  implementer_prompt, reviewer_prompt, budget_split, budget_usd,
  pass_rates, erosion_scores, verbosity_scores,
  tokens_implementer, tokens_reviewer, cost_per_checkpoint,
  total_pass_rate, total_cost, erosion_slope, verbosity_slope,
  baseline_pass_rate, delta_pass_rate, delta_erosion,
  manipulation_check, manipulation_notes, results_valid,
  impl_diff_summary
) VALUES (...);

UPDATE budget SET
  spent = spent + [actual_cost],
  remaining = total_budget - spent
WHERE id = 1;
```

**Exit criteria:** Row inserted, budget table updated. Run `gt done`.
"""
```

---

## 8. Data Model

### Experiments Table (Dolt)

Stores structured results for every experiment run. Created during
Phase 2 setup via `gt dolt sql`:

```sql
CREATE TABLE experiments (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  problem_id      VARCHAR(64) NOT NULL,
  model           VARCHAR(64) NOT NULL,
  mode            ENUM('single', 'two-agent') NOT NULL,
  hypothesis_id   VARCHAR(32),
  implementer_prompt VARCHAR(256),
  reviewer_prompt VARCHAR(256),
  budget_split    INT,
  budget_usd      DECIMAL(8,2),

  -- Per-checkpoint results (JSON arrays)
  pass_rates      JSON,
  erosion_scores  JSON,
  verbosity_scores JSON,
  tokens_implementer JSON,
  tokens_reviewer JSON,
  cost_per_checkpoint JSON,

  -- Aggregates
  total_pass_rate DECIMAL(5,2),
  total_cost      DECIMAL(8,2),
  erosion_slope   DECIMAL(8,4),
  verbosity_slope DECIMAL(8,4),

  -- Comparison
  baseline_pass_rate DECIMAL(5,2),
  delta_pass_rate    DECIMAL(5,2),
  delta_erosion      DECIMAL(8,4),

  -- Validation
  manipulation_check ENUM('passed', 'failed', 'skipped') DEFAULT 'skipped',
  manipulation_notes TEXT,
  results_valid      BOOLEAN DEFAULT FALSE,
  impl_diff_summary  TEXT
);
```

The Review Board queries this table. Only rows with
`manipulation_check = 'passed' AND results_valid = true` are included
in analysis.

### Budget Table (Dolt)

Single-row table tracking spend. The Mayor checks it at the top of
every patrol loop. This is the Mayor-level budget enforcement layer.

```sql
CREATE TABLE budget (
  id             INT PRIMARY KEY DEFAULT 1,
  total_budget   DECIMAL(8,2) NOT NULL,
  spent          DECIMAL(8,2) DEFAULT 0,
  remaining      DECIMAL(8,2) GENERATED ALWAYS AS (total_budget - spent),
  updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Initialize with ceiling
INSERT INTO budget (total_budget) VALUES (500.00);
```

### Knowledge Base (Beads)

The Idea Factory's research knowledge base is a beads epic
(`sc-research-kb`). Each finding is a bead with labels (`literature`,
`strategy`, `best-practice`, `dead-end`, `web-search`). Queried via
`bd search`, `bd list --label`, `bd list --parent`.

### Hypotheses (Beads)

A separate beads epic (`sc-hypotheses`). Each hypothesis stores
provenance in metadata JSON (`discovered_from` array pointing to KB
bead IDs), creating a traceable chain from literature -> hypothesis ->
experiment -> result. See Section 5 (Idea Factory) for the metadata
schema.

---

## 9. Budget Enforcement

Two layers of defense-in-depth:

### Layer 1: Mayor Gate (Dolt table)

The Mayor checks the budget table before each batch. Won't pour
molecules it can't afford.

```sql
SELECT remaining FROM budget WHERE id = 1;
```

If `remaining` < estimated batch cost, the Mayor reduces batch size or
enters shutdown. This is checked at Phase 0 of every research loop
iteration.

### Layer 2: Harness Cap (Runner script)

The two-agent runner script (`research/runner/two_agent_runner.py`)
tracks cumulative API cost during each run. If the per-experiment cap
(passed as `--budget`) is exceeded, the run aborts immediately and logs
partial results. This prevents a single runaway experiment from blowing
the remaining budget.

```python
if cumulative_cost > budget_cap:
    log.error(f"Budget cap exceeded: ${cumulative_cost:.2f} > ${budget_cap:.2f}")
    save_partial_results()
    sys.exit(1)
```

### Why Two Layers

The Mayor gate prevents dispatching batches that exceed the remaining
budget. But a single experiment could cost 10x expected (model pricing
change, retry storm, unexpectedly long problem). The harness cap is a
safety net that catches runaways before they drain the budget. Both are
cheap to implement.

---

## 10. Research Loop

The Mayor runs a continuous patrol:

```
Phase 0: BUDGET CHECK
  SELECT remaining FROM budget WHERE id = 1;
  If exhausted -> SHUTDOWN.
  If low -> reduce batch size.

Phase 1: ORIENT
  Dispatch Review Board polecat to query recent experiment results.
  Dispatch Idea Factory polecat to search web, update KB, propose
  hypotheses. Wait for both to complete (gt mail inbox).

Phase 2: PLAN
  Select 3-5 experiments from available hypotheses.
  File "Proposed Batch N" bead with rationale, configs, expected
  outcomes, budget estimate.

Phase 2.5: RED TEAM REVIEW (blocking)
  Create Red Team review bead that blocks the batch bead:

    bd create "Red Team Review: Batch N" --parent sc-reviews
    bd dep add sc-rt-review-N --blocks sc-batch-N
    gt sling sc-rt-review-N scbench

  Wait for Red Team to close review (batch appears in bd ready).
  Mayor addresses each objection in writing before Red Team closes.

Phase 3: EXECUTE
  Pour experiment molecules via gt convoy create:

    gt convoy create "Batch N" sc-exp-001 sc-exp-002 sc-exp-003 \
      --molecule mol-scbench-experiment \
      --notify mayor/ \
      --base-branch main

  Polecats execute in parallel: preflight -> implement -> peer review
  -> run baseline + two-agent -> validate -> report.
  Budget table updated after each experiment.

Phase 4: ANALYZE
  Dispatch Review Board polecat to query ledger (valid experiments
  only). Review Board files conclusion beads.

Phase 4.5: RED TEAM POST-MORTEM (advisory)
  Dispatch Red Team polecat to challenge Review Board's
  interpretation. Red Team files post-mortem bead. Not blocking, but
  Mayor reads it before proceeding.

Phase 5: DECIDE
  Mayor reads conclusions + post-mortem. Updates research log bead.
  Loop to Phase 0, or SHUTDOWN if research question is answered.
```

### Shutdown Sequence

On budget exhaustion or research completion:

1. Mayor files summary bead.
2. Dispatch Review Board polecat for final analysis.
3. Mayor writes `research/analysis/FINAL_REPORT.md`.
4. `gt escalate --severity critical --reason "SCBench research complete. Final report at research/analysis/FINAL_REPORT.md"`
5. Close all open beads.
6. `gt down`

---

## 11. Crash Resilience

### Dolt Data

Auto-committed after every write (auto-commit enabled). Configure a
Dolt remote for periodic push:

```bash
# Inside the scbench Dolt database
dolt remote add backup <remote-url>
```

The Deacon's existing backup dog handles periodic pushes. This covers
the experiments table, budget table, and all beads.

### Raw Experiment Outputs

Not in Dolt. A cron job (via `gt` daemon plugin or system cron) commits
and pushes `outputs/`, configs, scripts, and report files to git every
15 minutes:

```bash
*/15 * * * * cd ~/gt/scbench && git add -A outputs/ research/ && \
  git commit -m "auto: sync experiment outputs" && git push
```

### Recovery

`gt doctor --fix` repairs stale Gas Town state. The Mayor can resume
by checking `bd list --status in_progress` for interrupted experiments.
Poured molecules with checkpoint recovery resume from the last
completed step.

---

## 12. Notifications and Escalation

Gas Town's native escalation system handles all notifications. No
external webhooks needed.

| Event                  | Mechanism                                                    |
|------------------------|--------------------------------------------------------------|
| Budget exhausted       | `gt escalate --severity critical --reason "Budget exhausted"` |
| Preflight failure      | `gt escalate --severity high --related <hypothesis-id>`       |
| Manipulation check fail| `gt escalate --severity medium --related <hypothesis-id>`     |
| Research complete      | `gt escalate --severity critical --reason "Research complete"` |
| Polecat stuck          | Witness detects, routes through standard escalation           |

The Deacon routes escalations to the Mayor. Critical severity also
triggers email to the human operator (configured in
`settings/escalation.json`). Monitor progress via:

```bash
gt status                    # overall workspace state
gt convoy status             # experiment batch progress
gt costs --today --by-rig    # spend tracking
gt escalate list             # open escalations
```

---

## 13. Phased Implementation

### Phase 1 — Foundation (Days 1-3)

Fork slop-code-bench. Get it running on Brev. Run a single-agent
baseline on 2-3 problems. Build the two-agent runner script in
`research/runner/`. Run one manual two-agent experiment. Validate
Docker, API keys, and the pipeline end-to-end.

### Phase 2 — Gas Town (Days 4-6)

```bash
gt install            # if not already installed
gt rig add scbench <fork-url>
gt mayor attach scbench
```

Mayor-only mode — get comfortable with filing beads, pouring molecules.
Create the experiment formula TOML. Create Dolt tables:

```bash
gt dolt sql    # opens SQL shell
> CREATE TABLE experiments (...);
> CREATE TABLE budget (...);
> INSERT INTO budget (total_budget) VALUES (500.00);
```

Set up the git sync cron and Dolt remote. Create role beads for Idea
Factory, Review Board, Red Team. Create the KB epic
(`sc-research-kb`) and Hypotheses epic (`sc-hypotheses`).

### Phase 3 — Analytical Roles + Autonomy (Days 7-10)

Add Review Board polecat with role bead. Add Red Team polecat — test
adversarial review by having the Mayor propose a batch before adding
the Idea Factory. Verify that the `blocks` dependency enforces the
Red Team gate (batch doesn't appear in `bd ready` until review is
closed). Add Idea Factory polecat. Run the first fully autonomous
research loop. Monitor via `gt status`, `gt convoy status`.

### Phase 4 — Scale + Report (Days 11-14)

Scale to 3-5 parallel experiment polecats. Let the PI run multiple
autonomous loops within the budget ceiling. Verify escalation fires
on budget exhaustion. Compile results and package deliverable.

---

## 14. Budget Estimate

| Component                          | Estimate     |
|------------------------------------|--------------|
| Per experiment (baseline)          | $2-10        |
| Per experiment (two-agent)         | $3-15        |
| Per preflight canary               | $0.50        |
| Per batch (5 experiments)          | $25-75       |
| Red Team review per batch          | $2-5         |
| **Experiments (3-5 problems x 10-20 configs)** | **$200-500** |
| Orchestration (Mayor, analytical roles) | $50-100 |
| Red Team total                     | $20-50       |
| Preflight canaries                 | $5-10        |
| **Total estimated budget**         | **$300-650** |

Track actual spend via:

```bash
gt costs --today --by-rig     # daily spend by rig
gt dolt sql -q "SELECT spent, remaining FROM budget WHERE id = 1;"
```

---

## 15. Success Criteria

A deliverable that shows:

1. **Experimental evidence** — two-agent vs. single-agent on matched
   budgets across multiple problems, with per-checkpoint breakdowns.
2. **Identified sweet spots** — which configurations help, under what
   conditions, and by how much.
3. **Quality signal improvements** — reduced erosion and verbosity
   slopes.
4. **A working Gas Town research lab** — the autonomous loop, the
   research log showing the PI's reasoning, the Red Team's critiques.
5. **Reproducible methodology** — formulas, prompts, and configs
   anyone can rerun.

The narrative: "We used Gas Town to autonomously explore the design
space of a two-agent coding system on SlopCodeBench. The PI agent ran
N experiments across M problems, identified [pattern], and produced a
cost-vs-quality analysis showing [result]."

---

## Appendix A: Command Reference

Quick reference for the Gas Town commands used in this workspace.

| Task                        | Command                                              |
|-----------------------------|------------------------------------------------------|
| Start Mayor session         | `gt mayor attach scbench`                            |
| Add rig                     | `gt rig add scbench <url>`                           |
| Assign work to polecat      | `gt sling <bead-id> scbench`                         |
| Create convoy (batch)       | `gt convoy create "name" <beads...> --molecule <mol>` |
| Check batch progress        | `gt convoy status [convoy-id]`                       |
| Check workspace status      | `gt status`                                          |
| Check costs                 | `gt costs --today --by-rig`                          |
| Check budget (Dolt)         | `gt dolt sql -q "SELECT * FROM budget;"`             |
| Escalate                    | `gt escalate --severity <level> --reason "..."`      |
| List escalations            | `gt escalate list`                                   |
| Open SQL shell              | `gt dolt sql`                                        |
| Diagnose issues             | `gt doctor --fix`                                    |
| Send mail to agent          | `gt mail send <target> -s "subject"`                 |
| Check inbox                 | `gt mail inbox`                                      |
| Polecat completes work      | `gt done`                                            |
| Start autonomous mountain   | `gt mountain <epic-id>`                              |
| Check mountain progress     | `gt mountain status <id>`                            |

## Appendix B: Deviations from Original Spec

Changes made during architecture review:

| Original                     | Revised                                     | Rationale                                    |
|------------------------------|---------------------------------------------|----------------------------------------------|
| Crew members for analytical roles | Polecats with role beads               | Crew = human workspaces. Polecats + beads = stateless agents, stateful data. |
| `discovered-from` dependency type | Metadata JSON on hypothesis beads      | Provenance is annotation, not operational. Keeps dependency table clean. |
| Slack webhook notifications  | Native `gt escalate` + mail system          | Single human operator. No external dependency needed. |
| Red Team blocking via "patrol molecule" | `blocks` dependency on batch bead | Mechanical enforcement via existing `bd ready` system. |
| Budget enforcement assumed   | Two-layer: Mayor Dolt check + harness cap   | Gas Town tracks costs but doesn't enforce ceilings. Both layers needed. |
| `gt feed`                    | `gt status` + `gt convoy status`            | `gt feed` doesn't exist.                    |
| `gt shutdown`                | Shutdown sequence ending with `gt down`     | `gt shutdown` doesn't exist.                |
| `gt may at`                  | `gt mayor attach [rig]`                     | Correct command name.                        |
| Spec in gastown repo         | `research/spec.md` in slop-code-bench fork  | Fork is the rig. Spec belongs with experiment code. |
