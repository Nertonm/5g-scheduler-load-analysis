"""Testes dos contratos introduzidos por auditoria (2026-08-18/19)."""

import hashlib
import json
import os

import numpy as np
import pytest

from src.config import Config
from src.channel import channel_for_cfg, collect_snr_for_config, compute_rates
from src.analysis_metrics import jains_fairness_index, gini_index, j_family_chiang


def _cfg(enable_pathloss, alpha=3.0, **kw):
    return Config(
        num_ttis=200, num_seeds=1, user_counts=[4],
        schedulers=["empty"], save_results=False, generate_plots=False,
        enable_pathloss=enable_pathloss, pathloss_alpha=alpha, **kw,
    )


def _run(cfg, seeds=1, schedulers=("round_robin", "max_c_i")):
    import src.simulation as sim
    from src.config import Config as C
    c = C(**{**vars(cfg), "schedulers": list(schedulers), "save_results": False})
    return sim.run(c, seeds=list(range(seeds)))


def test_compute_rates_is_bit_per_second_and_monotone_in_regime():
    """compute_rates devolve positivo; monotona em |h| fora da regiao de cap."""
    cfg = _cfg(False)
    h = np.array([[0.1, 0.2], [0.3, 0.5], [0.7, 1.0], [1.5, 2.0]])
    rates = compute_rates(cfg, h)
    assert rates.shape == (4, 2)
    assert (rates > 0).all()
    assert (rates[:, 1] > rates[:, 0]).all()  # monotona por linha


def test_compute_rates_saturates_at_cap():
    """compute_rates aplica o cap de eficiencia espectral (decisao card 1)."""
    cfg = _cfg(False)
    h = np.array([[10.0, 100.0]])  # ambos |h|^2 >> 63 -> no cap
    rates = compute_rates(cfg, h)
    cap = cfg.occupied_bandwidth_hz * cfg.max_spectral_efficiency
    # ambos saturam no mesmo teto
    assert rates[0, 0] == pytest.approx(cap)
    assert rates[0, 1] == pytest.approx(cap)


def test_channel_for_cfg_respects_enable_pathloss():
    """channel_for_cfg alterna canal Rayleigh vs +path loss pelo Config."""
    sem = channel_for_cfg(_cfg(False), seed=7, num_ues=4, num_ttis=64)
    com = channel_for_cfg(_cfg(True), seed=7, num_ues=4, num_ttis=64)
    sem2 = channel_for_cfg(_cfg(False), seed=7, num_ues=4, num_ttis=64)
    assert np.array_equal(np.abs(sem.h).sum(), np.abs(sem2.h).sum())
    assert not np.allclose(np.abs(sem.h), np.abs(com.h))


def test_collect_snr_for_config_respects_pathloss():
    """collect_snr_for_config delega a channel_for_cfg; respeita path loss."""
    sem = collect_snr_for_config(_cfg(False), seed=11, num_ues=4, num_ttis=64)
    com = collect_snr_for_config(_cfg(True), seed=11, num_ues=4, num_ttis=64)
    assert not np.allclose(np.abs(sem.h), np.abs(com.h))
    with pytest.raises(NotImplementedError):
        collect_snr_for_config(Config(enable_pathloss=False, channel_model="uma"),
                               seed=1, num_ues=2)


def test_pipeline_run_respects_enable_pathloss():
    """simulation.run() muda de saida quando enable_pathloss alterna."""
    res_a = _run(_cfg(False), schedulers=("round_robin", "max_c_i"))
    res_b = _run(_cfg(True), schedulers=("round_robin", "max_c_i"))
    pa = res_a["per_ue"]["throughput_bps"]
    pb = res_b["per_ue"]["throughput_bps"]
    assert not np.allclose(pa, pb)


def test_analysis_metrics_expose_disjoint_fairness():
    """JFI de slots difere de JFI de vazao sob heterogeneidade."""
    # UE0 recebe 75% do tempo mas 90% da vazao -> vazao mais desbalanceada
    slots = np.array([6.0, 2.0])
    thr = np.array([9.0, 1.0])
    js = jains_fairness_index(slots)
    jt = jains_fairness_index(thr)
    assert jt < js


def test_manifest_receipt_matches_files():
    """Receipt nao-vence: SHA-256 e fingerprint dos arquivos conferem."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    man_path = os.path.join(repo, "results", "manifest-estudos.json")
    if not os.path.exists(man_path):
        pytest.skip("manifest-estudos.json ainda nao gerado")
    with open(man_path) as f:
        man = json.load(f)
    for name, meta in man.get("files", {}).items():
        p = os.path.join(repo, "results", name)
        assert os.path.exists(p), f"manifest cita {name} inexistente"
        digest = hashlib.sha256(open(p, "rb").read()).hexdigest()
        assert digest == meta["sha256"], f"SHA256 de {name} diverge do manifest"
    # O receipt canônico aponta para a fonte por seed e o resumo derivado.
    assert "estudo_per_seed.csv" in man["files"]
    assert "estudo_consolidado.csv" in man["files"]
    assert "50 seeds" in man["files"]["estudo_per_seed.csv"]["protocolo"]["corrida"]
    assert man["files"]["estudo_consolidado.csv"]["protocolo"]["fonte"] == "estudo_per_seed.csv"
    assert "seed" in man["files"]["estudo_umi_nlos.csv"]["protocolo"]["corrida"]
    # BLOQUEADOR (revisor): receipt NAO pode estar vencido. O tree_fingerprint
    # registrado deve bater com o fingerprint do worktree atual.
    from src.fingerprint import tree_fingerprint
    assert man.get("tree_fingerprint"), "receipt sem tree_fingerprint"
    atual = tree_fingerprint(repo)
    assert man["tree_fingerprint"] == atual, (
        "receipt VENCIDO: fingerprint registrado != candidate atual. "
        "Regenere com: python scripts/write_manifest.py"
    )


def test_gini_oracles():
    """Gini: 0 para igualdade, cresce com concentracao, zera detectado."""
    assert gini_index(np.array([1, 1, 1, 1])) == pytest.approx(0.0)
    # [4,0,0,0]: um detentor de tudo, demais zero -> 1 - 1/4 = 0.75
    assert gini_index(np.array([4, 0, 0, 0])) == pytest.approx(0.75)
    # mais igual que anterior -> menor
    assert gini_index(np.array([2, 2, 0, 0])) < gini_index(np.array([4, 0, 0, 0]))


def test_chiang_family_sanity():
    """Familia J_beta (Lan & Chiang eq 15 / n): Jain em beta=-1; [0,1] p/ beta<1."""
    import numpy as _np
    x31 = _np.array([3, 1])
    # 1) beta=-1 RECUPERA Jain exato
    assert j_family_chiang(x31, -1.0) == pytest.approx(jains_fairness_index(x31))
    assert j_family_chiang(x31, -1.0) == pytest.approx(0.8)
    # 2) concentracao total [4,0,0,0]: Jain = 0.25, e beta>=0 fica em [0,1]
    xc = _np.array([4, 0, 0, 0])
    assert j_family_chiang(xc, -1.0) == pytest.approx(0.25)
    assert 0 <= j_family_chiang(xc, 0.0) <= 1.0
    assert 0 <= j_family_chiang(xc, 0.5) <= 1.0
    # 3) igualdade -> 1 em qualquer beta valido
    ones = _np.array([1, 1, 1, 1])
    for b in [-1.0, 0.0, 0.5, 1.0]:
        assert j_family_chiang(ones, b) == pytest.approx(1.0)
    # 4) varredura beta monotona em [0,1] p/ vetor desigual
    vals = [j_family_chiang(x31, b) for b in [-3.0, -2.0, -1.0, 0.0, 0.5, 0.9]]
    assert all(0 <= v <= 1 for v in vals)
    assert vals == sorted(vals)
    # 5) mais justo -> maior (beta=-1)
    assert j_family_chiang(_np.array([5, 3, 2, 0]), -1.0) > j_family_chiang(_np.array([3, 1, 0, 0]), -1.0)
