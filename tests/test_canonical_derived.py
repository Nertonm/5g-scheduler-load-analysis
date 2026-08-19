import importlib.util
from pathlib import Path


def _load_study():
    path = Path(__file__).resolve().parents[1] / "scripts" / "estudo_consolidado.py"
    spec = importlib.util.spec_from_file_location("estudo_consolidado", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_canonical_study_owns_all_derived_analysis_builders():
    study = _load_study()
    assert callable(study.build_beta_summary)
    assert callable(study.build_bootstrap_summary)
