import importlib.util
from pathlib import Path

import pandas as pd


def _study_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "estudo_consolidado.py"
    spec = importlib.util.spec_from_file_location("estudo_consolidado", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_canonical_analysis_exports_required_figures(tmp_path):
    study = _study_module()
    rows = []
    for scheduler in ("RR", "MaxCI", "PF"):
        for pathloss, alpha in ((False, None), (True, 3.0)):
            for load in (2, 4):
                rows.append({
                    "sched": scheduler, "carga": load, "pathloss": pathloss, "alpha": alpha,
                    "jfi_slots_mean": 0.9, "jfi_slots_ci95": 0.01,
                    "jfi_throughput_mean": 0.8, "jfi_throughput_ci95": 0.02,
                    "gini_slots_mean": 0.1, "gini_throughput_mean": 0.2,
                    "jfi_win_mean": 0.85, "starv_max_mean": 20.0,
                    "j_beta_-3.0_mean": 0.7, "j_beta_-1.0_mean": 0.9,
                    "j_beta_+0.9_mean": 0.95,
                    "throughput_aggregate_bps_mean": 4e6, "throughput_aggregate_bps_ci95": 1e5, "thr_5pct_mean": 1e6, "nunca_mean": 0.0,
                })
    output = tmp_path / "figuras"
    study.export_figures(pd.DataFrame(rows), output)
    assert {p.name for p in output.glob("*.png")} == {
        "jfi_cenarios.png", "maxci_alpha.png", "borda_exclusao.png", "tradeoff_n32.png",
        "temporalidade.png", "robustez_metricas.png", "eficiencia_carga.png"
    }
