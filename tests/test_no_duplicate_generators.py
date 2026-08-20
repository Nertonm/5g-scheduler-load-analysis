from pathlib import Path


def test_obsolete_duplicate_generators_are_absent():
    root = Path(__file__).resolve().parents[1]
    scripts = root / "scripts"
    for name in ("estudo_expandido.py", "estudo_robusto.py", "estudo_injustica.py", "estudo_robustez_beta.py", "estudo_bootstrap_ld50.py", "estudo_umi_nlos.py", "estudo_hetero_4x.py"):
        assert not (scripts / name).exists(), f"gerador duplicado ainda ativo: {name}"
