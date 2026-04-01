#!/bin/bash
# setup_gastown.sh — Create Gas Town beads and install experiment formula
# for the SCBench research lab.
#
# Idempotent: checks before creating. Safe to re-run.
#
# Usage:
#   bash research/scripts/setup_gastown.sh
#
# Requires:
#   - bd and gt on PATH
#   - Gas Town workspace at ~/gt with scbench rig configured
#   - BEADS_DIR=~/gt/scbench/.beads (set automatically)

set -euo pipefail

export PATH="$PATH:/home/ubuntu/gopath/bin:/home/ubuntu/go/bin"
export BEADS_DIR="${BEADS_DIR:-$HOME/gt/scbench/.beads}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FORMULA_SRC="$REPO_ROOT/research/formulas/mol-scbench-experiment.formula.toml"
GT_ROOT="$HOME/gt"
GT_FORMULA_DIR="$GT_ROOT/.beads/formulas"

# --- Helpers ---

bead_exists() {
    bd show "$1" >/dev/null 2>&1
}

info() {
    echo "[setup] $*"
}

# --- Role Beads ---

if bead_exists sc-idea-factory-role; then
    info "sc-idea-factory-role already exists, skipping"
else
    info "Creating sc-idea-factory-role..."
    bd create "Idea Factory Role" \
        --id sc-idea-factory-role \
        --type task \
        --description "Builds a cumulative research knowledge base and generates hypotheses grounded in that knowledge. Each session: (1) Query the KB epic (sc-research-kb) via bd search, bd list --label, bd list --parent to rebuild context. (2) Actively search the web for relevant work: multi-agent coding strategies, code review automation, anti-slop techniques, SlopCodeBench discussions. (3) Log every finding as a KB bead under sc-research-kb before proposing any hypothesis. (4) Generate hypotheses as beads under sc-hypotheses with metadata containing discovered_from (KB bead IDs), testable_claim, predicted_outcome, and experiment_configs. Goal: every session leaves the KB richer than it found it." \
        --labels "role" \
        --no-history
fi

if bead_exists sc-review-board-role; then
    info "sc-review-board-role already exists, skipping"
else
    info "Creating sc-review-board-role..."
    bd create "Review Board Role" \
        --id sc-review-board-role \
        --type task \
        --description "Dispatched by Mayor after experiment batches complete. Queries the Dolt experiments table. ALWAYS filter on manipulation_check='passed' AND results_valid=true. Never include unverified experiments. Responsibilities: (1) Query experiments table with validation filters. (2) Identify patterns across experiments. (3) Compute statistical summaries: pass rate delta (two-agent minus baseline), erosion slope comparison, budget efficiency (cost per percentage point of pass rate). (4) File conclusion beads with numeric results. (5) Report how many experiments were excluded due to validation failures. Every Dolt query must include WHERE manipulation_check='passed' AND results_valid=true." \
        --labels "role" \
        --no-history
fi

if bead_exists sc-red-team-role; then
    info "sc-red-team-role already exists, skipping"
else
    info "Creating sc-red-team-role..."
    bd create "Red Team Role" \
        --id sc-red-team-role \
        --type task \
        --description "Adversarial reviewer that finds flaws before budget is burned and challenges interpretations after results land. Intervenes at two points: (1) Pre-dispatch (blocking): Mayor creates a Proposed Batch bead and a Red Team review bead. The review bead blocks the batch bead via a blocks dependency. File specific, actionable objections with numbered items containing problem, impact, and suggested fix. Zero-objection reviews violate contract. The batch bead will not appear in bd ready until the Red Team closes its review bead. (2) Post-results (advisory): After the Review Board analyzes results, challenge interpretation: does the data support the conclusion? What alternative explanations exist? Is sample size sufficient? File a post-mortem bead. This review is advisory and does not block downstream beads. The Red Team role is explicitly adversarial. It does not encourage, congratulate, or rubber-stamp. It finds problems." \
        --labels "role" \
        --no-history
fi

# --- Epic Beads ---

if bead_exists sc-research-kb; then
    info "sc-research-kb already exists, skipping"
else
    info "Creating sc-research-kb epic..."
    bd create "Research Knowledge Base" \
        --id sc-research-kb \
        --type epic \
        --description "Cumulative research knowledge base maintained by the Idea Factory. Every finding (papers, blog posts, strategies, best practices) is a child bead. Labels provide taxonomy: literature, strategy, best-practice, dead-end, web-search. Query via bd search, bd list --label, bd list --parent sc-research-kb." \
        --labels "kb,epic" \
        --no-history
fi

if bead_exists sc-hypotheses; then
    info "sc-hypotheses already exists, skipping"
else
    info "Creating sc-hypotheses epic..."
    bd create "Hypotheses" \
        --id sc-hypotheses \
        --type epic \
        --description "Parent epic for all research hypotheses. Each hypothesis bead stores provenance in its metadata field: discovered_from (array of KB bead IDs), testable_claim, predicted_outcome, experiment_configs. Hypotheses are generated by the Idea Factory and tested via experiment molecules." \
        --labels "hypotheses,epic" \
        --no-history
fi

# --- Mayor Research Log ---

if bead_exists sc-research-log; then
    info "sc-research-log already exists, skipping"
else
    info "Creating sc-research-log..."
    bd create "Mayor Research Log" \
        --id sc-research-log \
        --type task \
        --description "Persistent research log maintained by the Mayor (PI agent). The running narrative of what has been tried, what was learned, and what comes next. This log is the persistent memory that survives across sessions. Append entries via bd note sc-research-log." \
        --labels "log,mayor" \
        --no-history \
        --notes "=== Research Log Initialized ===
This log tracks the full arc of the SCBench two-agent research project.
Each entry records: decisions made, experiments dispatched, results observed, strategy updates.
Append new entries with: bd note sc-research-log \"<entry>\""
fi

# --- Install Formula ---

if [ ! -f "$FORMULA_SRC" ]; then
    echo "ERROR: Formula source not found at $FORMULA_SRC" >&2
    exit 1
fi

mkdir -p "$GT_FORMULA_DIR"
cp "$FORMULA_SRC" "$GT_FORMULA_DIR/"
info "Formula installed to $GT_FORMULA_DIR/"

# --- Verify ---

info ""
info "=== Verification ==="

ERRORS=0

for bead in sc-idea-factory-role sc-review-board-role sc-red-team-role \
            sc-research-kb sc-hypotheses sc-research-log; do
    if bead_exists "$bead"; then
        info "  ✓ $bead"
    else
        info "  ✗ $bead MISSING"
        ERRORS=$((ERRORS + 1))
    fi
done

if cd "$GT_ROOT" && gt formula show mol-scbench-experiment >/dev/null 2>&1; then
    info "  ✓ mol-scbench-experiment formula registered"
else
    info "  ✗ mol-scbench-experiment formula NOT found"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "ERROR: $ERRORS verification failures" >&2
    exit 1
fi

info ""
info "Gas Town setup complete. All beads and formula verified."
