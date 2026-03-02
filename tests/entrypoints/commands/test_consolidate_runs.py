from __future__ import annotations

from slop_code.entrypoints.commands.consolidate_runs import EXPECTED_MASS_COLS
from slop_code.entrypoints.commands.consolidate_runs import check_mass_columns


def _build_complete_mass_record() -> dict[str, float]:
    return dict.fromkeys(EXPECTED_MASS_COLS, 1.0)


def test_check_mass_columns_passes_when_all_expected_present():
    record = _build_complete_mass_record()

    assert check_mass_columns(record) is False


def test_check_mass_columns_fails_when_complexity_concentration_missing():
    record = _build_complete_mass_record()
    del record["mass.complexity_concentration"]

    assert check_mass_columns(record) is True


def test_check_mass_columns_fails_when_try_scaffold_concentration_missing():
    record = _build_complete_mass_record()
    del record["mass.try_scaffold_concentration"]

    assert check_mass_columns(record) is True
