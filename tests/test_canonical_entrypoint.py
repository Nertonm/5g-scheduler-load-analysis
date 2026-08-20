from pathlib import Path


def test_make_study_has_one_canonical_entrypoint():
    root = Path(__file__).resolve().parents[1]
    makefile = (root / "Makefile").read_text()
    study_block = makefile.split("estudo:\n", 1)[1].split("\nreceipt:", 1)[0]
    assert "python scripts/estudo_consolidado.py --seeds 50" in study_block
    assert "estudo_expandido.py" not in study_block
    assert "estudo_robustez_beta.py" not in study_block
    assert "estudo_bootstrap_ld50.py" not in study_block
