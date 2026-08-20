"""Smoke test: o ambiente está saudável e a configuração do projeto é válida.

Estes testes rodam do container (make test) e são a porta de entrada
mais barata para detectar regressão de ambiente antes de rodar simulação cara.

O que cada teste verifica:
- test_sionna_importable: o Sionna (motor da simulação) está instalado.
- test_numpy_scipy_pandas: a stack científica está completa. Cada módulo é
  testado separadamente para que uma falha diga QUAL dependência falta.
- test_project_config_loads: a Config carrega, os valores críticos batem com o
  desenho do experimento, e os tipos numéricos estão corretos (protege contra
  regressão para strings, o bug que o YAML causava).
"""

import importlib.util
import sys
from pathlib import Path


def test_sionna_importable():
    """Sionna precisa existir no site-packages do container."""
    spec = importlib.util.find_spec("sionna")
    assert spec is not None, "Sionna não está instalado no ambiente"


def test_numpy_scipy_pandas():
    """Stack científica obrigatória para análise e gráficos."""
    for mod in ["numpy", "scipy", "pandas", "matplotlib", "seaborn"]:
        spec = importlib.util.find_spec(mod)
        assert spec is not None, f"{mod} não está instalado"


def test_statsmodels_importable():
    """statsmodels é necessário para regressão logística e análise estatística."""
    spec = importlib.util.find_spec("statsmodels")
    assert spec is not None, "statsmodels não está instalado"

def test_sklearn_importable():
    """scikit-learn é necessário para machine learning e métricas de apoio."""
    spec = importlib.util.find_spec("sklearn")
    assert spec is not None, "scikit-learn não está instalado"

def test_project_config_loads():
    """A Config carrega com valores e tipos corretos."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.config import load_config

    cfg = load_config()

    # Valores do desenho (checkpoint seção 5). Se mudarem, é mudança de desenho.
    assert cfg.user_counts == [2, 4, 8, 16, 32], "cargas de UEs divergem do desenho"
    assert cfg.schedulers == [
        "round_robin",
        "max_c_i",
        "proportional_fair",
    ], "schedulers divergem do desenho"
    assert cfg.num_ttis == 10000, "TTIs divergem do desenho"
    assert cfg.num_seeds == 50, "seeds divergem do desenho"
    assert cfg.is_siso is True, "cenário deve ser SISO (decisão metodológica)"
    assert cfg.link_direction == "downlink", "enlace deve ser downlink (alinhado no checkpoint)"
    assert cfg.traffic == "full_buffer", "tráfego deve ser full-buffer (alinhado no checkpoint)"
    assert cfg.export_per_ue is True, "deve exportar throughput por UE (base das metricas derivadas)"
    assert "delta_jfi_relative_to_rr" in cfg.metrics

    # Tipos numéricos corretos (o bug do YAML tratava 20e6 como string)
    assert isinstance(cfg.bandwidth_hz, float), "bandwidth deve ser float"
    assert isinstance(cfg.subcarrier_spacing_hz, float), "subcarrier deve ser float"
    assert isinstance(cfg.carrier_freq_hz, float), "carrier_freq deve ser float"
    assert isinstance(cfg.tti_duration, float), "tti_duration deve ser float"

    # Propriedades derivadas
    assert abs(cfg.occupied_bandwidth_hz - 18.72e6) < 1e-6  # 52 * 12 * 30 kHz
    assert cfg.sim_duration_per_seed_s == 10.0  # 10000 * 1 ms
