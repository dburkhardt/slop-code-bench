-- setup_dolt.sql
-- Creates experiments and budget tables for the SCBench Research Lab.
-- Idempotent: safe to run multiple times (uses IF NOT EXISTS and
-- INSERT IGNORE).
--
-- Usage:
--   cd ~/gt/.dolt-data/scbench && dolt sql < research/scripts/setup_dolt.sql
-- Or from the repo root:
--   cd ~/gt/.dolt-data/scbench && dolt sql < /home/ubuntu/git-repos/slop-code-bench/research/scripts/setup_dolt.sql

-- ---------------------------------------------------------------
-- Experiments table (27 columns)
-- Stores structured results for every experiment run.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiments (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    problem_id          VARCHAR(64) NOT NULL,
    model               VARCHAR(64) NOT NULL,
    mode                ENUM('single', 'two-agent') NOT NULL,
    hypothesis_id       VARCHAR(32),
    implementer_prompt  VARCHAR(256),
    reviewer_prompt     VARCHAR(256),
    budget_split        INT,
    budget_usd          DECIMAL(8,2),

    -- Per-checkpoint results (JSON arrays)
    pass_rates          JSON,
    erosion_scores      JSON,
    verbosity_scores    JSON,
    tokens_implementer  JSON,
    tokens_reviewer     JSON,
    cost_per_checkpoint JSON,

    -- Aggregates
    total_pass_rate     DECIMAL(5,2),
    total_cost          DECIMAL(8,2),
    erosion_slope       DECIMAL(8,4),
    verbosity_slope     DECIMAL(8,4),

    -- Comparison
    baseline_pass_rate  DECIMAL(5,2),
    delta_pass_rate     DECIMAL(5,2),
    delta_erosion       DECIMAL(8,4),

    -- Validation
    manipulation_check  ENUM('passed', 'failed', 'skipped')
                        DEFAULT 'skipped',
    manipulation_notes  TEXT,
    results_valid       BOOLEAN DEFAULT FALSE,
    impl_diff_summary   TEXT
);

-- ---------------------------------------------------------------
-- Budget table (5 columns, single-row)
-- Tracks total spend. The Mayor checks remaining at the top of
-- every patrol loop. remaining is a generated column.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS budget (
    id           INT PRIMARY KEY DEFAULT 1,
    total_budget DECIMAL(8,2) NOT NULL,
    spent        DECIMAL(8,2) DEFAULT 0.00,
    remaining    DECIMAL(8,2) GENERATED ALWAYS AS
                 (total_budget - spent),
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                 ON UPDATE CURRENT_TIMESTAMP
);

-- Initialize budget with $500 ceiling (idempotent: only inserts if
-- no row with id=1 exists yet).
INSERT INTO budget (id, total_budget, spent)
SELECT 1, 500.00, 0.00
WHERE NOT EXISTS (SELECT 1 FROM budget WHERE id = 1);
