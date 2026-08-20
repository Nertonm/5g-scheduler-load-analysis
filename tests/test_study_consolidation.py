"""Contratos do estudo consolidado, pareado por seed."""

import pandas as pd
import pytest


def _rows():
    rows = []
    for pathloss in (False, True):
        for seed, value in enumerate((0.2, 0.4)):
            rows.append(
                {
                    "sched": "MaxCI",
                    "carga": 4,
                    "pathloss": pathloss,
                    "alpha": 3.0 if pathloss else None,
                    "seed": seed,
                    "jfi_slots": value,
                    "jfi_throughput": value / 2,
                    "jfi_win": value,
                    "starv_p95": 10.0,
                    "starv_max": 20.0,
                    "thr_5pct": 1_000_000.0,
                    "nunca": 1.0,
                    "gini_slots": 1.0 - value,
                    "gini_throughput": 1.0 - value / 2,
                    "j_beta_-3.0": value,
                    "j_beta_-2.0": value,
                    "j_beta_-1.0": value,
                    "j_beta_+0.0": value,
                    "j_beta_+0.5": value,
                    "j_beta_+0.9": value,
                }
            )
    return pd.DataFrame(rows)


def test_aggregate_preserves_both_pathloss_arms_and_all_metrics():
    from src.study_results import aggregate_per_seed

    result = aggregate_per_seed(_rows())
    assert len(result) == 2
    assert set(result["pathloss"]) == {False, True}
    assert set(result["seed_count"]) == {2}
    assert result.loc[result["pathloss"], "jfi_slots_mean"].item() == pytest.approx(0.3)
    assert "gini_slots_mean" in result.columns
    assert "j_beta_-1.0_mean" in result.columns
    assert "thr_5pct_ci95" in result.columns


def test_aggregate_requires_same_seed_set_per_pathloss_arm():
    from src.study_results import validate_paired_seed_sets

    frame = _rows().query("not (pathloss and seed == 1)")
    errors = validate_paired_seed_sets(frame)
    assert errors == [
        "sched=MaxCI carga=4 alpha=3.0: seeds sem_pathloss=[0, 1] com_pathloss=[0]"
    ]
