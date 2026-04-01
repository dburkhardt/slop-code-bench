# Checkpoint Results Schema

`checkpoint_results.jsonl` rows are flattened metric records, not nested
pass-count objects.

Observed fields used by the harness include:

- `strict_pass_rate`
- `isolated_pass_rate`
- `erosion`
- `verbosity`
- `cost`

Do not assume `pass_counts` or `total_counts` keys are present in each row.

Code references:

- `src/slop_code/metrics/checkpoint/driver.py`
- `src/slop_code/metrics/checkpoint/extractors.py`
