"""Metricas de analise para o estudo de injustica do Max C/I.

Complementam o JFI agregado (que sob UEs homogeneos nao varia com a carga)
com tres medidas sensiveis a dinamic temporal:

- sliding-window JFI: justica de curto prazo em janelas deslizantes.
- starvation: intervalos entre alocacoes consecutivas de um mesmo UE
  (percentil 95 / maximo), captura a latencia de acesso.
- 5th percentile de throughput: desempenho de "cell edge" intra-seed.

Nao altera o pipeline (src/simulation.py); e codigo de analise.
"""

from __future__ import annotations

import numpy as np


def jains_fairness_index(x: np.ndarray) -> float:
    """J = (sum x)^2 / (n * sum x^2), de 1/n a 1 (Jain, Chiu & Hawe 1984)."""
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return float("nan")
    s = x.sum()
    if s == 0:
        return float("nan")
    return float((s * s) / (x.size * (x * x).sum()))


def sliding_window_jfi(alloc: np.ndarray, num_ues: int, window: int) -> float:
    """JFI medio sobre janelas deslizantes nao sobrepostas de tamanho `window`.

    alloc: vetor [T] com o UE escalonado a cada TTI (0..num_ues-1).
    window: tamanho da janela (recomendado multiplo de num_ues).
    Retorna a media do JFI computado sobre a contagem de slots por janela.
    """
    alloc = np.asarray(alloc, dtype=np.int64)
    T = alloc.size
    if window <= 0:
        raise ValueError("window deve ser > 0")
    vals = []
    for start in range(0, T - window + 1, window):
        seg = alloc[start:start + window]
        counts = np.bincount(seg, minlength=num_ues).astype(np.float64)
        vals.append(jains_fairness_index(counts))
    return float(np.mean(vals)) if vals else float("nan")


def starvation_percentile(
    alloc: np.ndarray, num_ues: int, percentile: float = 95.0
) -> float:
    """Percentil dos intervalos (TTIs) entre alocacoes de um mesmo UE.

    Para cada UE, difere as posicoes em que ele foi escalonado; a distribuicao
    conjunta dos gaps (sobre todos os UEs) e o objeto. Retorna o percentil
    pedido.

    LIMITACAO (confirmada na auditoria P2): UEs com menos de 2 alocacoes
    (incluindo nunca atendidos) NAO contribuem para a distribuicao, e gaps
    inicial/final (antes da 1a e depois da ultima alocacao) sao ignorados.
    Sob exclusao, o p95 cai artificialmente e pode sugerir latencia baixa
    quando muitos UEs estao de fato excluidos. Nao use esta metrica isolada;
    reporte junto de starvation_max_of() e nunca_* (contagem de UEs sem
    alocacao), que capturam a exclusao total.
    """
    alloc = np.asarray(alloc, dtype=np.int64)
    gaps = []
    for ue in range(num_ues):
        idx = np.where(alloc == ue)[0]
        if len(idx) >= 2:
            gaps.extend(np.diff(idx).tolist())
    if not gaps:
        return float("nan")
    return float(np.percentile(gaps, percentile))


def throughput_5th_percentile(per_ue_throughput: np.ndarray) -> float:
    """5o percentil do throughput por UE numa janela/seed.

    per_ue_throughput: vetor [num_ues] de vazão média por UE (bit/s).
    """
    return float(np.percentile(np.asarray(per_ue_throughput), 5))


def gini_index(x: np.ndarray) -> float:
    """Coeficiente de Gini (0 = igualdade perfeita, 1 = concentracao total).

    Calculado sobre o vetor COMPLETO (zeros contam como partes sem recurso):
        G = (2 * sum_{i=1..n} i * x_(i)) / (n * sum_i x_i) - (n+1)/n
    com x_(i) ordenado CRESCENTE. Shares iguais -> 0; um unico detentor de tudo
    (demais zeros) -> 1 - 1/n (aproxima 1 com n grande). E uma metrica de
    concentracao complementar ao JFI (prevista no trabalho IAD); nao e uma
    medida de justica normalizada em [0,1] no mesmo sentido do JFI, mas e
    monotona com a desigualdade. Não pertence à família $J_\beta$ e não há
    uma conversão geral simples entre Gini e JFI.
    """
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return float("nan")
    x = np.sort(x)  # crescente; zeros permanecem
    n = x.size
    total = x.sum()
    if total == 0:
        return float("nan")
    numer = 2.0 * np.dot(np.arange(1, n + 1), x)
    return float(numer / (n * total) - (n + 1.0) / n)


def j_family_chiang(x, beta=-1.0):
    """Familia f_beta de Lan & Chiang (eq. 15, arXiv:0906.0557), indexada.

    Formula primaria (r=1) do paper, eq. (15):
        f_beta(x) = sign(1-beta) * [ sum_i ( x_i / sum_j x_j )^(1-beta) ]^(1/beta)
    Em beta = -1 recupera o **indice de Jain**:  J(x) = f_{-1}(x) / n,
    porque a media harmonica e usada no Axioma 4 (ver Sec. II-D do paper).

    Esta funcao devolve J_beta(x) = f_beta(x) / n (a generalizacao de Jain
    normalizada), de modo que: igualdade perfeita -> 1; um unico detentor de
    tudo (demais zeros) -> 1/n. Domínio valido: beta < 1 (para beta > 1 as
    medidas sao negativas; sinal de 1-beta). beta = 0 e o caso entropia
    (limite da eq. 15, generator log); beta = 1 e o caso PF (proporcional),
    limites 1 e n (J=1).

    Exemplos: [3,1] -> Jain=0.8 (beta=-1); [4,0,0,0] -> 0.25 (um detentor).
    """
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return float("nan")
    tot = x.sum()
    n = x.size
    if tot <= 0:
        return float("nan")
    p = x / tot              # shares: soma = 1
    if abs(beta - 1.0) < 1e-9:
        # beta=1: limitante (PF); f/n -> 1 (igualdade) ... normaliza como limite
        # f_1 = n, logo J_1 = 1
        return 1.0
    if abs(beta) < 1e-9:
        # beta=0: caso entropia (limite da eq. 15 com generator log)
        # f_0 = exp(-sum p_i log p_i)  (em nats); J_0 = f_0 / n
        # p_i=0 contribui 0*log0 = 0
        # evita log(0): computa apenas onde p>0 (0*log0 = 0 p/ a entropia)
        mask = p > 0
        logp = np.zeros_like(p)
        with np.errstate(divide='ignore', invalid='ignore'):
            logp[mask] = np.log(p[mask])
        H = -float(np.dot(p, logp))       # entropia de Shannon (nats)
        return float(np.exp(H) / n)
    sign = 1.0 if (1 - beta) > 0 else -1.0
    base = np.power(p, 1.0 - beta).sum()
    if base == 0:
        return float("nan")
    f = sign * np.power(base, 1.0 / beta)
    return float(f / n)
