import importlib.util
from pathlib import Path

import numpy as np
import pytest


def _study_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "estudo_consolidado.py"
    spec = importlib.util.spec_from_file_location("estudo_consolidado", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_alloc_metrics_exports_cell_efficiency_and_per_ue_mean():
    study = _study_module()
    rates = np.array([[10.0, 5.0], [2.0, 8.0], [6.0, 4.0], [3.0, 7.0]])
    allocation = np.array([0, 1, 0, 1])
    metrics = study.alloc_metrics(allocation, 2, rates)
    assert metrics["throughput_aggregate_bps"] == pytest.approx((10 + 8 + 6 + 7) / 4)
    assert metrics["throughput_mean_per_ue_bps"] == pytest.approx((10 + 8 + 6 + 7) / 8)
