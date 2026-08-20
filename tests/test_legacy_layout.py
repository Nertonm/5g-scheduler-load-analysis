from pathlib import Path


def test_legacy_outputs_are_not_on_the_canonical_results_surface():
    root = Path(__file__).resolve().parents[1] / "results"
    legacy = {
        "cdf_throughput.csv",
        "estudo_expandido.csv",
        "estudo_logdistance_v2.csv",
        "estudo_robusto.csv",
        "manifest.json",
        "results_per_seed.csv",
        "results_summary.csv",
    }
    assert (root / "legado" / "README.md").is_file()
    assert all(not (root / name).exists() for name in legacy)
    assert not (root / "_historico").exists()
