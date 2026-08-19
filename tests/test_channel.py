"""Testes do módulo de canal (Card 1); determinísticos, rodam em CPU.

Roda dentro do container: make test (docker compose exec sionna pytest).
Testes de shape/determinismo usam batch pequeno; os de distribuição usam
10^4 TTIs (o call inteiro leva segundos em CPU).
"""

import numpy as np
import torch

from src.channel import generate_channel, noise_power_w
from src.config import load_config
from sionna.phy import config as sionna_config
from sionna.phy.channel import RayleighBlockFading


def test_shapes_e_dtypes():
    """Shapes/dtypes: h [T,N] complex64, tau zero (canal SISO 1 path)."""
    r = generate_channel(seed=0, num_ues=4, num_ttis=64)
    assert r.h.shape == (64, 4)
    assert r.h.dtype == np.complex64
    assert r.gains.shape == (64, 4)
    assert r.gains.dtype == np.float32
    assert np.all(r.tau == 0.0)


def test_determinismo_mesma_seed():
    """Mesma seed -> mesmo canal bit a bit (reprodutibilidade)."""
    a = generate_channel(seed=42, num_ues=8, num_ttis=128).h
    b = generate_channel(seed=42, num_ues=8, num_ttis=128).h
    assert np.array_equal(a, b)  # bit a bit em CPU


def test_seeds_diferentes():
    """Seeds distintas -> canais distintos (amostra independente)."""
    a = generate_channel(seed=1, num_ues=8, num_ttis=128).h
    b = generate_channel(seed=2, num_ues=8, num_ttis=128).h
    assert not np.array_equal(a, b)


def test_distribuicao_unit_variance():
    """Verifica CN(0,1): E|h|^2=1 e var partes real/imag = 0.5 cada."""
    r = generate_channel(seed=0, num_ues=8, num_ttis=10000)
    g = r.gains
    assert abs(g.mean() - 1.0) < 0.05  # E|h|^2 = 1 (Exp(1))
    assert abs(g.std() - 1.0) < 0.1
    h = r.h
    assert abs(h.real.var() - 0.5) < 0.05
    assert abs(h.imag.var() - 0.5) < 0.05


def test_homogeneidade_entre_ues():
    """Sem path loss, todos os UEs tem a mesma distribuicao de ganho."""
    r = generate_channel(seed=0, num_ues=16, num_ttis=10000)
    means = r.gains.mean(axis=0)
    assert np.max(means) - np.min(means) < 0.05  # mesma distribuição p/ todos


def test_block_fading_constante_no_tempo():
    """num_time_steps replica o coeficiente.

    Por isso o padrão de produção usa batch=TTIs com num_time_steps=1.
    """
    sionna_config.seed = 3
    m = RayleighBlockFading(num_rx=1, num_rx_ant=1, num_tx=1, num_tx_ant=1)
    a, _ = m(batch_size=2, num_time_steps=14)
    assert torch.allclose(a[:, 0, 0, 0, 0, 0, 0], a[:, 0, 0, 0, 0, 0, 13])


def test_torch_manual_seed_nao_controla_canal():
    """torch.manual_seed sozinho não é o mecanismo canônico (config.seed é)."""
    sionna_config.seed = 42
    m1 = RayleighBlockFading(num_rx=2, num_rx_ant=1, num_tx=1, num_tx_ant=1)
    x1, _ = m1(batch_size=50, num_time_steps=1)
    torch.manual_seed(42)
    x2, _ = m1(batch_size=50, num_time_steps=1)
    # O canal segue o gerador do config; re-setar só o torch não reproduz.
    assert not torch.equal(x1, x2)


def test_ruido_termico():
    """Ruido k_B*T*B: checa o valor analitico para 18.72 MHz @ 300K."""
    assert abs(noise_power_w(18.72e6, 300.0) - 1.380649e-23 * 300.0 * 18.72e6) < 1e-20


def test_snr_referencia_e_homogenea():
    """SNR media por UE converge para a referencia; homogenea entre UEs."""
    cfg = load_config()
    r = generate_channel(seed=0, num_ues=4, num_ttis=10000)
    per_ue = r.mean_snr_db_per_ue(10.0)  # média linear -> dB, por UE
    assert abs(per_ue.mean() - 10.0) < 0.2  # SNR média == referência
    assert np.max(per_ue) - np.min(per_ue) < 0.2  # homogênea por construção


def test_restaura_seed_global():
    """generate_channel restaura o config.seed anterior (try/finally)."""
    sionna_config.seed = 999
    _ = generate_channel(seed=7, num_ues=2, num_ttis=32)
    assert sionna_config.seed == 999
