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
    """Config minimo: 200 TTIs, 1 seed, scheduler vazio, CSV em tmp_path."""
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
    """Pipeline completo roda com scheduler vazio (card 1)."""
    out = run(cfg_tmp)
    assert "per_ue" in out and "per_seed" in out and "summary" in out
    assert len(out["per_seed"]) == 2  # 2 cargas x 1 seed x 1 scheduler


def test_per_ue_csv_schema(cfg_tmp):
    """Schema do per_ue: colunas fixas e cardinalidade N x seeds."""
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
    """Schema do per_seed: uma linha por (scheduler, carga, seed)."""
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
    """EmptyScheduler: throughput 0 e JFI NaN (guard all-zero)."""
    out = run(cfg_tmp)
    per_ue = out["per_ue"]
    assert (per_ue["throughput_bps"] == 0.0).all()
    assert (per_ue["slots_allocated"] == 0).all()
    assert (per_ue["prbs_allocated"] == 0).all()
    assert out["per_seed"]["jains_fairness_index"].isna().all()  # all-zero -> NaN


def test_three_schedulers_run_grid_and_allocate(cfg_tmp):
    """Integração dos cards 5-7: os 3 schedulers (RR, Max C/I, PF) rodam o
    grid real via run() (não só o factory) e alocam. Cada UE recebe
    throughput > 0; só 'empty' dá zeros (coberto em test_empty_allocates_nothing).
    """
    cfg_tmp.save_results = False
    cfg_tmp.schedulers = ["round_robin", "max_c_i", "proportional_fair"]
    out = run(cfg_tmp)
    per_ue = out["per_ue"]
    per_seed = out["per_seed"]

    # 2 cargas x 1 seed x 3 schedulers
    assert set(per_ue["scheduler"].unique()) == {
        "round_robin",
        "max_c_i",
        "proportional_fair",
    }
    assert len(per_seed) == 6

    for sched in ["round_robin", "max_c_i", "proportional_fair"]:
        sub = per_ue[per_ue["scheduler"] == sched]
        assert (sub["throughput_bps"] > 0).all(), f"{sched} não alocou"
        assert (sub["slots_allocated"] > 0).all(), f"{sched} sem slots"
        jfi = per_seed.loc[per_seed["scheduler"] == sched, "jains_fairness_index"]
        assert not jfi.isna().all(), f"{sched} com JFI NaN (sem alocação)"

    # RR: ciclo perfeito (card 2) => cada UE recebe exatamente N_TTI / N slots
    rr = per_ue[per_ue["scheduler"] == "round_robin"]
    for carga, grp in rr.groupby("carga"):
        n = int(carga)
        assert (grp["slots_allocated"] == cfg_tmp.num_ttis // n).all()

    # Max C/I: total agregado >= RR (argmax por TTI domina o ciclo; card 3)
    agg = per_seed.groupby("scheduler")["throughput_aggregate_bps"].sum()
    assert agg["max_c_i"] > agg["round_robin"]

    # card 6: resultados distintos entre as políticas (JFI não idênticos)
    jfi = per_seed.groupby("scheduler")["jains_fairness_index"].mean()
    assert len(set(jfi.round(6))) >= 2


def test_determinism_same_seed(cfg_tmp):
    """Mesma seed -> mesmos resultados bit a bit (CPU)."""
    cfg_tmp.save_results = False
    a = run(cfg_tmp)["per_ue"]
    b = run(cfg_tmp)["per_ue"]
    pd.testing.assert_frame_equal(a, b)


def test_seed_changes_channel():
    """Seeds distintas -> canais e resultados distintos."""
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
    """Oráculos do JFI: igualdade=1, [1,0,0]->1/3, all-zero->NaN."""
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
    """Escrita atomica nao deixa .tmp para tras (os.replace)."""
    run(cfg_tmp)
    import glob

    assert glob.glob(f"{cfg_tmp.results_dir}/**/*.tmp", recursive=True) == []


def test_write_atomic(tmp_path):
    """write_csv_atomic grava e o conteudo lido bate com o DataFrame."""
    df = pd.DataFrame({"a": [1, 2]})
    p = tmp_path / "x.csv"
    write_csv_atomic(str(p), df)
    assert pd.read_csv(p)["a"].tolist() == [1, 2]
