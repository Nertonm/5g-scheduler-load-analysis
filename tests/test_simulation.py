"""Testes do loop base + estrutura de saída (Card 1).

Roda dentro do container: make test. Usa num_ttis pequeno e scheduler
vazio ('empty' é o comportamento default do card 1) para suíte rápida.
"""

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.simulation import (
    jains_fairness_index,
    run,
    write_csv_atomic,
)


@pytest.fixture()
def cfg_tmp(tmp_path):
    return Config(
        num_ttis=200,
        num_seeds=1,
        user_counts=[2, 4],
        schedulers=["empty"],
        export_per_ue=True,
        save_results=True,
        results_dir=str(tmp_path),
        generate_plots=False,
    )


def test_loop_empty_smoke(cfg_tmp):
    out = run(cfg_tmp)
    assert "per_ue" in out and "per_seed" in out and "summary" in out
    assert len(out["per_seed"]) == 2  # 2 cargas x 1 seed x 1 scheduler


def test_per_ue_csv_schema(cfg_tmp):
    run(cfg_tmp)
    import os

    # header do CSV per-UE
    path = os.path.join(cfg_tmp.results_dir, "per_ue", "empty__carga2__seed0.csv")
    df = pd.read_csv(path)
    assert list(df.columns) == [
        "scheduler",
        "carga",
        "seed",
        "ue_id",
        "throughput_bps",
        "slots_allocated",
        "prbs_allocated",
    ]


def test_per_seed_csv_schema(cfg_tmp):
    run(cfg_tmp)
    import os

    path = os.path.join(cfg_tmp.results_dir, "results_per_seed.csv")
    df = pd.read_csv(path)
    assert list(df.columns) == [
        "scheduler",
        "carga",
        "seed",
        "throughput_aggregate_bps",
        "throughput_mean_per_ue_bps",
        "jains_fairness_index",
        "throughput_5th_percentile_bps",
        "delta_jfi_relative_to_rr",
        "mean_snr_db_per_ue",
    ]
    assert len(df) == 2


def test_empty_allocates_nothing(cfg_tmp):
    out = run(cfg_tmp)
    per_ue = out["per_ue"]
    assert (per_ue["throughput_bps"] == 0.0).all()
    assert (per_ue["slots_allocated"] == 0).all()
    assert (per_ue["prbs_allocated"] == 0).all()
    assert out["per_seed"]["jains_fairness_index"].isna().all()  # all-zero -> NaN


def test_determinism_same_seed(cfg_tmp):
    cfg_tmp.save_results = False
    a = run(cfg_tmp)["per_ue"]
    b = run(cfg_tmp)["per_ue"]
    pd.testing.assert_frame_equal(a, b)


def test_seed_changes_channel():
    cfg = Config(
        num_ttis=64, num_seeds=1, user_counts=[4], schedulers=["empty"],
        save_results=False,
    )
    cfg2 = Config(
        num_ttis=64, num_seeds=1, user_counts=[4], schedulers=["empty"],
        save_results=False,
    )
    # seeds diferentes => canais diferentes => rates diferentes
    from src.channel import compute_rates, generate_channel

    h1 = generate_channel(seed=0, num_ues=4, num_ttis=64).h
    h2 = generate_channel(seed=1, num_ues=4, num_ttis=64).h
    assert not np.array_equal(h1, h2)
    r1 = compute_rates(cfg, h1)
    r2 = compute_rates(cfg2, h2)
    assert not np.array_equal(r1, r2)


def test_jfi_math():
    assert jains_fairness_index([1, 1, 1]) == 1.0
    assert abs(jains_fairness_index([1, 0, 0]) - 1.0 / 3.0) < 1e-12
    assert np.isnan(jains_fairness_index([0, 0, 0]))


def test_throughput_formula():
    """Canal sintético |h|^2=1 => thr == W_occ * log2(1+gamma) (hand-computed)."""
    from src.channel import compute_rates
    from src.config import load_config

    cfg = load_config()
    h = np.ones((10, 4), dtype=np.complex64)
    r = compute_rates(cfg, h)
    gamma = 10.0 ** (cfg.snr_db / 10.0)
    expected = cfg.occupied_bandwidth_hz * np.log2(1.0 + gamma)
    assert np.allclose(r, expected)


def test_atomic_write_cleanup(cfg_tmp):
    run(cfg_tmp)
    import glob

    assert glob.glob(f"{cfg_tmp.results_dir}/**/*.tmp", recursive=True) == []


def test_write_atomic(tmp_path):
    df = pd.DataFrame({"a": [1, 2]})
    p = tmp_path / "x.csv"
    write_csv_atomic(str(p), df)
    assert pd.read_csv(p)["a"].tolist() == [1, 2]
