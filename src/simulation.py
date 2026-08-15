"""Loop base da simulação + estrutura de saída (Card 1).

Card 1 entrega a estrutura, não a política: o scheduler é vazio (nada é
alocado, throughput = 0.0) e a interface para os schedulers dos cards 2-4
fica documentada abaixo, mas não implementada aqui (escopo do card 1).

Contrato que src/schedulers.py (cards 2-4) deve expor para encaixar
sem refatoração:

    class Scheduler(Protocol):
        def select(self, tti: int, rates: np.ndarray) -> int:
            \"\"\"rates: [N] float, taxa instantânea realizável (bit/s, banda
            cheia) de cada UE no TTI. Retorna índice 0..N-1 do UE
            escalonado, ou -1 (nenhum UE, scheduler vazio).\"\"\"
        def update(self, tti: int, ue: int, rate: float) -> None:
            \"\"\"Hook pós-alocação (PF atualiza média com a taxa alcançada;
            RR e Max C/I: no-op).\"\"\"

O registry ``create_scheduler(name, cfg, num_ues)`` vive nos cards 2-4.

Loop: carga -> seed -> canal (uma vez por (carga, seed)) -> scheduler -> TTI.
O canal gerado uma vez e compartilhado entre schedulers garante pareamento
perfeito para o t-pareado do card 8 e para delta_jfi_relative_to_rr.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict

import numpy as np
import pandas as pd

from .channel import compute_rates, generate_channel
from .config import Config, load_config


# Scheduler vazio (card 1), embutido aqui para não invadir o escopo dos
# cards 2-4. Os schedulers reais virão em src/schedulers.py.
class EmptyScheduler:
    """Não aloca nada: select sempre -1, update no-op.

    Resultado: throughput_bps = 0.0 para todos os UEs e
    jains_fairness_index = NaN (guarda all-zero). O pipeline completo
    (canal, rate, acumulação, CSV, métricas) roda do início ao fim.
    """

    def __init__(self, num_ues: int) -> None:
        self.num_ues = num_ues

    def select(self, tti: int, rates: np.ndarray) -> int:
        return -1

    def update(self, tti: int, ue: int, rate: float) -> None:
        return None


# Métricas derivadas (as que são escalares por seed)
def jains_fairness_index(x: np.ndarray) -> float:
    """J = (sum x)^2 / (n * sum x^2), de 1/n a 1. Jain, Chiu & Hawe 1984.

    Guarda all-zero -> NaN (0/0 indefinido), para não reportar justiça
    onde não há alocação.
    """
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return float("nan")
    s = x.sum()
    if s == 0.0:
        return float("nan")
    return float((s * s) / (x.size * (x * x).sum()))


# Núcleo do loop
def run_seed_on_rates(
    cfg: Config, name: str, carga: int, seed: int, rates: np.ndarray
) -> pd.DataFrame:
    """Roda um scheduler sobre as rates de (carga, seed); retorna DF per-UE.

    rates: [num_ttis, carga] float64 (bit/s). Scheduler vazio no card 1.
    """
    num_ues = carga
    sched = EmptyScheduler(num_ues=num_ues)
    bits = np.zeros(num_ues, dtype=np.float64)
    slots = np.zeros(num_ues, dtype=np.int64)

    for t in range(cfg.num_ttis):
        ue = sched.select(t, rates[t])
        if ue >= 0:
            bits[ue] += rates[t, ue] * cfg.tti_duration
            slots[ue] += 1
            sched.update(t, ue, rates[t, ue])

    thr = bits / cfg.sim_duration_per_seed_s  # bit/s por UE
    return pd.DataFrame(
        {
            "scheduler": name,
            "carga": carga,
            "seed": seed,
            "ue_id": np.arange(num_ues),
            "throughput_bps": thr,
            "slots_allocated": slots,
            "prbs_allocated": slots * cfg.num_prbs,
        }
    )


def build_per_seed_row(
    cfg: Config, per_ue: pd.DataFrame, mean_snr_db: float
) -> dict:
    """Métricas escalares por (scheduler, carga, seed), espelhando cfg.metrics.

    A coluna delta_jfi_relative_to_rr existe desde o card 1 (NaN enquanto
    não houver RR) para o schema não mudar no card 5.

    mean_snr_db: SNR média temporal por UE (linear, depois dB) na seed.
    Homogênea por construção (sem path loss), o escalar representa a seed.
    """
    thr = per_ue["throughput_bps"].to_numpy(dtype=np.float64)
    aggregate = float(thr.sum())
    return {
        "scheduler": per_ue["scheduler"].iloc[0],
        "carga": int(per_ue["carga"].iloc[0]),
        "seed": int(per_ue["seed"].iloc[0]),
        "throughput_aggregate_bps": aggregate,
        "throughput_mean_per_ue_bps": aggregate / len(thr),
        "jains_fairness_index": jains_fairness_index(thr),
        "throughput_5th_percentile_bps": float(np.percentile(thr, 5)),
        "delta_jfi_relative_to_rr": float("nan"),  # exige RR (cards 2-4)
        "mean_snr_db_per_ue": float(mean_snr_db),
    }


def write_csv_atomic(path, df: pd.DataFrame) -> None:
    """Escrita atômica (tmp + os.replace); crash nunca deixa CSV parcial."""
    tmp = f"{path}.tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


# API pública
def run(
    cfg: Config,
    schedulers: list[str] | None = None,
    cargas: list[int] | None = None,
    seeds: list[int] | None = None,
) -> dict[str, pd.DataFrame]:
    """Executa o grid (card 1: scheduler vazio).

    Retorna dict com 'per_ue' (concatenado), 'per_seed', 'summary' e 'cdf'.
    Se cfg.save_results, grava em cfg.results_dir:
        per_ue/<scheduler>__cargaN__seedM.csv
        results_per_seed.csv, results_summary.csv, cdf_throughput.csv
        manifest.json
    Se cfg.save_results=False, retorna os DataFrames sem gravar (testes).
    """
    names = schedulers if schedulers is not None else cfg.schedulers
    loads = cargas if cargas is not None else cfg.user_counts
    run_seeds = seeds if seeds is not None else list(range(cfg.num_seeds))

    # Card 1 só implementa o scheduler vazio. Rejeitar nomes reais evita
    # gerar CSVs round_robin__... com zeros que pareceriam resultado.
    for name in names:
        if name != "empty":
            raise NotImplementedError(
                f"scheduler {name!r} não implementado no card 1; use 'empty'"
            )

    started = time.time()
    completed: list[str] = []
    per_ue_frames: list[pd.DataFrame] = []
    per_seed_rows: list[dict] = []

    results_dir = cfg.results_dir
    per_ue_dir = os.path.join(results_dir, "per_ue")
    if cfg.save_results:
        os.makedirs(per_ue_dir, exist_ok=True)

    total = len(names) * len(loads) * len(run_seeds)
    done = 0

    # Canal uma vez por (carga, seed): todos os schedulers rodam sobre o
    # MESMO tensor, garantindo pareamento perfeito para o t-pareado do
    # card 8 e para delta_jfi_relative_to_rr.
    for carga in loads:
        for seed in run_seeds:
            real = generate_channel(seed=seed, num_ues=carga, num_ttis=cfg.num_ttis)
            rates = compute_rates(cfg, real.h)  # [T, N] float64

            for name in names:
                df_ue = run_seed_on_rates(cfg, name, carga, seed, rates)
                per_ue_frames.append(df_ue)
                mean_snr_db = float(real.mean_snr_db_per_ue(cfg.snr_db).mean())
                per_seed_rows.append(build_per_seed_row(cfg, df_ue, mean_snr_db))

                if cfg.save_results:
                    fname = f"{name}__carga{carga}__seed{seed}.csv"
                    write_csv_atomic(os.path.join(per_ue_dir, fname), df_ue)
                    completed.append(f"{name}|{carga}|{seed}")

                done += 1
                if done % 10 == 0 or done == total:
                    print(f"[simulation] {done}/{total}", flush=True)

    per_ue_all = pd.concat(per_ue_frames, ignore_index=True)
    per_seed = pd.DataFrame(per_seed_rows)

    # Summary: IC 95% por (scheduler, carga); unidade amostral = seed.
    summary_rows = []
    for (sched, carga), grp in per_seed.groupby(["scheduler", "carga"]):
        n = len(grp)
        mean = grp["throughput_aggregate_bps"].mean()
        std = grp["throughput_aggregate_bps"].std(ddof=1)
        se = std / np.sqrt(n)
        # t(0.975, n-1): scipy não é obrigatório aqui; 1.96 é assintótico,
        # mas para n=20 o t exato é ~2.093. Importar scipy se disponível.
        try:
            from scipy import stats

            tcrit = stats.t.ppf(0.975, df=n - 1)
        except ImportError:
            tcrit = 1.96
        summary_rows.append(
            {
                "scheduler": sched,
                "carga": carga,
                "metric": "throughput_aggregate_bps",
                "mean": mean,
                "std": std,
                "ci95_low": mean - tcrit * se,
                "ci95_high": mean + tcrit * se,
            }
        )
    summary = pd.DataFrame(summary_rows)

    # CDF empírica pooled por (scheduler, carga)
    cdf_rows = []
    for (sched, carga), grp in per_ue_all.groupby(["scheduler", "carga"]):
        vals = np.sort(grp["throughput_bps"].to_numpy())
        m = len(vals)
        cdf_rows.extend(
            [
                {"scheduler": sched, "carga": carga, "throughput_bps": v, "cdf": (i + 1) / m}
                for i, v in enumerate(vals)
            ]
        )
    cdf = pd.DataFrame(cdf_rows)

    if cfg.save_results:
        write_csv_atomic(os.path.join(results_dir, "results_per_seed.csv"), per_seed)
        write_csv_atomic(os.path.join(results_dir, "results_summary.csv"), summary)
        write_csv_atomic(os.path.join(results_dir, "cdf_throughput.csv"), cdf)
        manifest = {
            "config": asdict(cfg),
            "wall_time_s": round(time.time() - started, 2),
            "completed": completed,
            "git_commit": _git_commit(),
        }
        manifest_path = os.path.join(results_dir, "manifest.json")
        manifest_tmp = f"{manifest_path}.tmp"
        with open(manifest_tmp, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        os.replace(manifest_tmp, manifest_path)

    return {"per_ue": per_ue_all, "per_seed": per_seed, "summary": summary, "cdf": cdf}


def _git_commit() -> str:
    """SHA do HEAD do repo (para reprodutibilidade do manifest)."""
    try:
        import subprocess

        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


if __name__ == "__main__":
    run(load_config())
