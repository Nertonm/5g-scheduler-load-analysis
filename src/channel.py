"""Canal Rayleigh + coleta de SNR (Card 1).

Contato único com o Sionna para geração de canal. Nada aqui sabe de
scheduler; a política de escalonamento entra pelos cards 2-4.

API verificada (2026-08-15, container sionna 2.0.1 torch):
- ``RayleighBlockFading(num_rx, num_rx_ant, num_tx, num_tx_ant)``: as
  antenas são obrigatórias (sem elas, TypeError). SISO downlink = num_tx=1
  (gNB), num_rx=N_UEs, num_rx_ant=num_tx_ant=1.
- Block fading: o coeficiente é sorteado UMA vez por exemplo do batch e
  replicado em ``num_time_steps`` (h.expand). Portanto o padrão correto
  para TTIs i.i.d. é ``batch_size=num_ttis, num_time_steps=1``; cada TTI
  é um exemplo de batch independente. Nunca ``num_time_steps=num_ttis``
  (congelaria o canal na seed inteira e destruiria a diversidade
  multiusuário temporal).
- Seed canônica: ``sionna.phy.config.seed`` (singleton global que re-semeia
  os RNGs por device). ``torch.manual_seed`` não controla o canal.
- Distribuição: h ~ CN(0,1) (E|h|^2=1), tau = delay único zero.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from sionna.phy import config as sionna_config
from sionna.phy.channel import RayleighBlockFading
from sionna.phy.constants import BOLTZMANN_CONSTANT

from .config import Config


@dataclass(frozen=True)
class ChannelRealization:
    """Uma realização do canal para (seed, carga).

    h:   [num_ttis, num_ues] complex64, coeficientes do fading, CN(0,1).
    tau: [num_ttis, num_ues, 1] float32, atrasos (zeros, caminho único).
    """

    h: np.ndarray
    tau: np.ndarray
    seed: int
    num_ues: int
    num_ttis: int

    @property
    def gains(self) -> np.ndarray:
        """|h|^2 por UE por TTI: [num_ttis, num_ues] float32, ~ Exp(1)."""
        return np.abs(self.h) ** 2

    def snr_linear(self, snr_ref_linear: float) -> np.ndarray:
        """SNR linear por UE por TTI = snr_ref_linear * |h|^2.

        Como E|h|^2 = 1, E[SNR] = snr_ref_linear; a SNR média é
        homogênea entre UEs por construção (sem path loss/shadowing).
        """
        return snr_ref_linear * self.gains

    def snr_db(self, snr_ref_db: float) -> np.ndarray:
        """SNR em dB por UE por TTI: [num_ttis, num_ues]."""
        ref_lin = 10.0 ** (snr_ref_db / 10.0)
        return 10.0 * np.log10(self.snr_linear(ref_lin))

    def mean_snr_db_per_ue(self, snr_ref_db: float) -> np.ndarray:
        """SNR média (linear, depois dB) por UE: [num_ues].

        É o agregado que verifica a homogeneidade: os valores por UE devem
        convergir para ``snr_ref_db`` dentro do erro amostral
        (SE ~ 0.056 dB com 10^4 TTIs).
        """
        return 10.0 * np.log10(self.snr_linear(10.0 ** (snr_ref_db / 10.0)).mean(axis=0))


def build_channel_model(
    num_ues: int,
    *,
    precision: str | None = None,
    device: str | None = None,
) -> RayleighBlockFading:
    """SISO downlink: num_tx=1 (gNB), num_rx=num_ues (UEs), antenas=1."""
    return RayleighBlockFading(
        num_rx=num_ues,
        num_rx_ant=1,
        num_tx=1,
        num_tx_ant=1,
        precision=precision,
        device=device,
    )


def generate_channel(
    seed: int,
    num_ues: int,
    num_ttis: int,
    *,
    precision: str = "single",
    device: str | None = None,
) -> ChannelRealization:
    """Gera a série completa do canal de uma seed em um único call.

    batch_size=num_ttis, num_time_steps=1: cada TTI é um exemplo de batch
    independente (block fading replica o eixo tempo, não o batch).

    Determinismo: seta ``sionna.phy.config.seed`` e restaura o valor
    anterior (try/finally). O config é singleton global; vazar o seed
    alterado corromperia a reprodutibilidade dos cards seguintes.
    """
    prev_seed = sionna_config.seed
    try:
        sionna_config.seed = seed
        model = build_channel_model(num_ues, precision=precision, device=device)
        a, tau = model(batch_size=num_ttis, num_time_steps=1)
    finally:
        sionna_config.seed = prev_seed

    # [num_ttis, num_ues, 1, 1, 1, 1, 1] -> squeeze seguro porque os eixos
    # restantes são todos 1 (SISO, 1 path). Se num_paths>1 no futuro, usar
    # indexação explícita.
    h = a[:, :, 0, 0, 0, 0, 0].numpy()  # complex64
    t = tau[:, :, 0].numpy()  # float32 [num_ttis, num_ues, 1]
    return ChannelRealization(h=h, tau=t, seed=seed, num_ues=num_ues, num_ttis=num_ttis)


def noise_power_w(bandwidth_hz: float, temperature_k: float = 300.0) -> float:
    """Ruído térmico: k_B * T * B (W). B = banda ocupada.

    Fórmula canônica dos tutoriais Sionna: no = BOLTZMANN_CONSTANT * T * B.
    Para 18.72 MHz @ 300 K: ~7.75e-13 W.
    """
    return BOLTZMANN_CONSTANT * temperature_k * bandwidth_hz


def compute_rates(cfg: Config, h: np.ndarray) -> np.ndarray:
    """Taxa instantânea realizável por UE por TTI: [num_ttis, num_ues] bit/s.

    Shannon com cap (decisão do card 1, documentada no config):
        rate = W_occ * min(log2(1 + gamma * |h|^2), max_se)
    com gamma = 10^(snr_db/10) e W_occ = cfg.occupied_bandwidth_hz.

    - Sem tabela MCS (TS 38.214) no card 1: monotônica, preserva os argmax
      de Max C/I e a ordenação de PF. O objetivo é comparar schedulers
      entre si, não absolutos com 5G NR real.
    - Canal flat (1 path, delay 0): a taxa é idêntica em todos os PRBs do
      TTI, então alocar PRBs individuais não muda nada; o TTI inteiro
      (52 PRBs) vai para o UE escalonado.
    """
    gamma = 10.0 ** (cfg.snr_db / 10.0)
    snr = gamma * np.abs(h) ** 2
    se = np.minimum(np.log2(1.0 + snr), cfg.max_spectral_efficiency)
    return cfg.occupied_bandwidth_hz * se


def positions_from_seed(seed: int, num_ues: int, radius_m: float = 500.0) -> np.ndarray:
    """Posicoes deterministica dos UEs (x, y) no disco de raio ``radius_m``.

    Semeadas por ``seed``: mesma seed -> mesma geometria (reprodutivel).
    Amostragem uniforme no disco via r = R*sqrt(u), theta ~ U(0, 2pi).
    Retorna [num_ues, 2] com (x, y).
    """
    prng = np.random.default_rng(1000 + seed)
    r = radius_m * np.sqrt(prng.uniform(0.0, 1.0, num_ues))
    th = prng.uniform(0.0, 2.0 * np.pi, num_ues)
    return np.stack([r * np.cos(th), r * np.sin(th)], axis=1)


def log_distance_gain(distance_m: np.ndarray, alpha: float, d0_m: float = 10.0) -> np.ndarray:
    """Ganho relativo de potencia por path loss log-distance.

    Modelo da disciplina de redes sem fio:  P(d) = P0 * (d0/d)^alpha  (alpha 2 a 4;
    2=espaco livre, 3-4 urbano denso). ``distance_m`` plano da celula; d0 a
    distancia de referencia (evita divisao por zero e singularidade na origem).
    """
    d = np.maximum(np.asarray(distance_m, dtype=np.float64), d0_m)
    return (d0_m / d) ** float(alpha)


def apply_pathloss(h: np.ndarray, positions: np.ndarray, alpha: float, d0_m: float = 10.0) -> np.ndarray:
    """Aplica path loss log-distance ao canal, por UE.

    h: [num_ttis, num_ues] complex64 (canal Rayleigh do Sionna).
    positions: [num_ues, 2] (x, y) dos UEs, com a BS na origem.
    Retorna h escalado: cada UE k recebe o ganho sqrt(gamma_k), com
    gamma_k = (d0/d_k)^alpha (o canal é multiplicado por raiz do ganho de
    potencia; a SNR media de cada UE fica proporcional a gamma_k,
    heterogenea entre UEs por distancia - a fonte da injustica do Max C/I).
    """
    d = np.sqrt((positions ** 2).sum(axis=1))  # [num_ues] distancia 2D ao gNB
    gamma = log_distance_gain(d, alpha, d0_m)
    # normaliza para SNR media ~= 1 em media (nao muda a ordenacao entre UEs)
    gamma = gamma / gamma.mean()
    # cast do fator para o dtype de h (complex64) evita promocao para complex128
    factor = np.sqrt(gamma).astype(h.dtype, copy=False)
    return h * factor[None, :]


def generate_channel_with_pathloss(
    seed: int, num_ues: int, num_ttis: int, alpha: float,
    *, radius_m: float = 500.0, d0_m: float = 10.0,
    precision: str = "single", device: str | None = None,
) -> ChannelRealization:
    """Canal Rayleigh + path loss log-distance (cena heterogenea near/far).

    Gera o canal Rayleigh (como ``generate_channel``) e aplica o path loss
    log-distance por posicao de UE (funcao ``apply_pathloss``). As posicoes
    sao deterministicas do seed: mesma seed -> mesma geometria + mesmo canal.
    O objeto retornado e a mesma ``ChannelRealization`` (h ja escalado).
    As posicoes usadas ficam acessiveis via ``positions_from_seed(seed, num_ues)``.
    """
    real = generate_channel(seed=seed, num_ues=num_ues, num_ttis=num_ttis,
                            precision=precision, device=device)
    positions = positions_from_seed(seed, num_ues, radius_m)
    h_scaled = apply_pathloss(real.h, positions, alpha, d0_m)
    # ChannelRealization e dataclass frozen; reconstroi o objeto com o h escalado.
    return ChannelRealization(h=h_scaled, tau=real.tau, seed=seed,
                              num_ues=num_ues, num_ttis=num_ttis)


def channel_for_cfg(cfg: Config, seed: int, num_ues: int, num_ttis: int | None = None,
                    precision: str = "single", device: str | None = None) -> ChannelRealization:
    """Gera o canal respeitando o Config (inclui path loss se cfg.enable_pathloss).

    Ponto unico de decisao de canal para estudos: se ``cfg.enable_pathloss`` e
    True, aplica path loss log-distance com ``cfg.pathloss_alpha`` (e d0/raio do
    config); senao, canal Rayleigh puro. ``num_ttis`` default = cfg.num_ttis.
    """
    if num_ttis is None:
        num_ttis = cfg.num_ttis
    if cfg.enable_pathloss:
        return generate_channel_with_pathloss(
            seed, num_ues, num_ttis, cfg.pathloss_alpha,
            radius_m=cfg.pathloss_radius_m, d0_m=cfg.pathloss_d0_m,
            precision=precision, device=device,
        )
    return generate_channel(seed=seed, num_ues=num_ues, num_ttis=num_ttis,
                            precision=precision, device=device)


def collect_snr_for_config(cfg: Config, seed: int, num_ues: int, num_ttis: int | None = None) -> ChannelRealization:
    """Integração com o config: gera o canal de (seed, carga) com os
    parâmetros do desenho. Delega a `channel_for_cfg`, que respeita
    `cfg.enable_pathloss` (aplica path loss log-distance quando habilitado)
    e `cfg.channel_model`. Suporta apenas 'rayleigh' no card 1."""
    if cfg.channel_model != "rayleigh":
        raise NotImplementedError(
            f"channel_model={cfg.channel_model!r} não suportado no card 1"
        )
    return channel_for_cfg(cfg, seed, num_ues,
                           num_ttis if num_ttis is not None else cfg.num_ttis)
