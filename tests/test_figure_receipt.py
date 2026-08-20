import hashlib
import json
from pathlib import Path


def test_receipt_hashes_exported_figures():
    root = Path(__file__).resolve().parents[1]
    receipt = json.loads((root / "results" / "manifest-estudos.json").read_text())
    figures = receipt["figures"]
    assert set(figures) == {
        "figuras/jfi_cenarios.png", "figuras/maxci_alpha.png", "figuras/borda_exclusao.png", "figuras/tradeoff_n32.png", "figuras/temporalidade.png", "figuras/robustez_metricas.png", "figuras/eficiencia_carga.png"
    }
    for relative, meta in figures.items():
        path = root / "results" / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"]
