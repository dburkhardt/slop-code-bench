from __future__ import annotations

import json

from rich.console import Console

from slop_code.common import SUMMARY_FILENAME
from slop_code.entrypoints.utils import display_and_save_summary


def test_display_and_save_summary_uses_complexity_mass_gini_for_erosion(
    tmp_path,
):
    results_file = tmp_path / "checkpoint_results.jsonl"
    rows = [
        {
            "problem": "prob1",
            "idx": 1,
            "pass_rate": 1.0,
            "checkpoint_pass_rate": 1.0,
            "functions": 5,
            "methods": 0,
            "loc": 100,
            "mass.complexity_concentration": 0.6,
        },
        {
            "problem": "prob1",
            "idx": 2,
            "pass_rate": 1.0,
            "checkpoint_pass_rate": 1.0,
            "functions": 5,
            "methods": 0,
            "loc": 100,
            "mass.complexity_concentration": 0.4,
        },
    ]
    results_file.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    config = {
        "model": {"name": "test-model"},
        "thinking": "none",
        "prompt_path": "test_prompt.jinja",
        "agent": {"type": "test-agent", "version": "v1"},
    }
    console = Console(record=True)

    summary = display_and_save_summary(results_file, tmp_path, config, console)

    assert summary is not None
    expected_first = 0.6
    expected_second = 0.4
    assert summary.erosion.mean == (expected_first + expected_second) / 2
    assert summary.erosion.count == 2

    saved = json.loads((tmp_path / SUMMARY_FILENAME).read_text())
    assert saved["erosion"]["mean"] == summary.erosion.mean
