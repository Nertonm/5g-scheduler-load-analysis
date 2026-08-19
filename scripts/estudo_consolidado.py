"""Estudo canônico pareado de schedulers, sem e com path loss.

Cada cenário usa as mesmas seeds 0..N-1 para RR, MaxCI e PF. O CSV por seed é
fonte de verdade; o CSV consolidado deriva todas as métricas dessa fonte.
"""

import argparse
import os
import sys
import time
from pathlib import Path

for cand in (os.getcwd(), os.path.join(os.getcwd(), ".."), "/workspace"):
    if os.path.isdir(os.path.join(cand, "src")) and cand not in sys.path:
        sys.path.insert(0, cand)
        break

import numpy as np
import pandas as pd

from src.analysis_metrics import (
    gini_index,
    j_family_chiang,
    jains_fairness_index,
    sliding_window_jfi,
    starvation_percentile,
    throughput_5th_percentile,
)
from src.channel import channel_for_cfg, compute_rates, generate_channel
from src.config import Config
from src.schedulers import MaxCIScheduler, ProportionalFair, RoundRobin
from src.study_results import aggregate_per_seed, validate_paired_seed_sets

SCHED = {"RR": RoundRobin, "MaxCI": MaxCIScheduler, "PF": ProportionalFair}
BETAS = (-3.0, -2.0, -1.0, 0.0, 0.5, 0.9)
SCENARIOS = ((False, None),) + tuple((True, alpha) for alpha in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0))


def run_seed(cls, rates: np.ndarray, num_ues: int, beta: float = 0.98) -> np.ndarray:
    scheduler = cls(num_ues=num_ues, beta=beta) if cls is ProportionalFair else cls(num_ues=num_ues)
    allocation = np.empty(rates.shape[0], dtype=int)
    for tti, instantaneous_rates in enumerate(rates):
        ue = scheduler.select(tti, instantaneous_rates)
        allocation[tti] = ue
        scheduler.update(tti, ue, float(instantaneous_rates[ue]))
    return allocation


def observed_starvation_max(allocation: np.ndarray, num_ues: int) -> int:
    """Maior gap interno observado, não uma latência censurada no horizonte."""
    maximum = 0
    for ue in range(num_ues):
        positions = np.flatnonzero(allocation == ue)
        if len(positions) >= 2:
            maximum = max(maximum, int(np.diff(positions).max()))
    return maximum


def alloc_metrics(allocation: np.ndarray, num_ues: int, rates: np.ndarray) -> dict[str, object]:
    """Métricas por seed, idênticas para os braços sem e com path loss."""
    slots = np.bincount(allocation, minlength=num_ues).astype(float)
    throughput_bps = np.zeros(num_ues)
    for ue in range(num_ues):
        throughput_bps[ue] = rates[allocation == ue, ue].sum() / len(allocation)

    result: dict[str, object] = {
        "jfi_slots": jains_fairness_index(slots),
        "jfi_throughput": jains_fairness_index(throughput_bps),
        "jfi_win": sliding_window_jfi(allocation, num_ues, num_ues * 10),
        "starv_p95": starvation_percentile(allocation, num_ues, 95),
        "starv_max": observed_starvation_max(allocation, num_ues),
        "throughput_aggregate_bps": float(throughput_bps.sum()),
        "throughput_mean_per_ue_bps": float(throughput_bps.mean()),
        "thr_5pct": throughput_5th_percentile(throughput_bps),
        "nunca": int((slots == 0).sum()),
        "gini_slots": gini_index(slots),
        "gini_throughput": gini_index(throughput_bps),
        "slots_vec": ",".join(str(int(value)) for value in slots),
        "thr_vec": ",".join(f"{value:.3f}" for value in throughput_bps),
    }
    for beta in BETAS:
        result[f"j_beta_{beta:+.1f}"] = j_family_chiang(slots, beta)
    return result


def build(cfg_base: Config, seeds: int = 50, ttis: int = 10_000, out_dir: str = "results") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Gera um estudo pareado completo e seu resumo derivado.

    O mesmo seed gera o mesmo Rayleigh de base no braço homogêneo e em cada
    braço log-distance. Assim comparações sem/com path loss usam o mesmo índice
    de seed, o mesmo scheduler e o mesmo conjunto completo de métricas.
    """
    rows: list[dict[str, object]] = []
    started = time.time()
    for pathloss, alpha in SCENARIOS:
        cfg = Config(**{**vars(cfg_base), "enable_pathloss": pathloss, "pathloss_alpha": alpha or cfg_base.pathloss_alpha})
        for carga in cfg.user_counts:
            for seed in range(seeds):
                realization = channel_for_cfg(cfg, seed, carga, ttis)
                rates = compute_rates(cfg, realization.h)
                for name, cls in SCHED.items():
                    allocation = run_seed(cls, rates, carga, beta=cfg.pf_beta)
                    rows.append(
                        {
                            "sched": name,
                            "carga": carga,
                            "pathloss": pathloss,
                            "alpha": alpha if pathloss else None,
                            "seed": seed,
                            **alloc_metrics(allocation, carga, rates),
                        }
                    )
            print(f"scenario pathloss={pathloss} alpha={alpha} carga={carga} elapsed={time.time() - started:.0f}s", flush=True)

    per_seed = pd.DataFrame(rows)
    errors = validate_paired_seed_sets(per_seed)
    if errors:
        raise RuntimeError("pareamento de seeds invalido: " + "; ".join(errors))
    consolidated = aggregate_per_seed(per_seed)

    os.makedirs(out_dir, exist_ok=True)
    per_seed_path = os.path.join(out_dir, "estudo_per_seed.csv")
    consolidated_path = os.path.join(out_dir, "estudo_consolidado.csv")
    per_seed.to_csv(per_seed_path, index=False)
    consolidated.to_csv(consolidated_path, index=False)
    print(f"saved {per_seed_path}: {len(per_seed)} rows")
    print(f"saved {consolidated_path}: {len(consolidated)} rows")
    return per_seed, consolidated



def scenario_label(pathloss: bool, alpha: float | None) -> str:
    return "homogeneo" if not pathloss else f"a={float(alpha):.1f}"


def bootstrap_ci(values: np.ndarray, rng: np.random.Generator, repeats: int = 2000) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    indexes = rng.integers(0, len(values), size=(repeats, len(values)))
    means = values[indexes].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def exploratory_ld50(loads: np.ndarray, means: np.ndarray) -> float:
    """Cruzamento exploratório de cinco médias, sem IC inferencial."""
    y = (np.asarray(means) < 0.5).astype(float)
    if len(np.unique(y)) < 2:
        return float("nan")
    x = np.log(np.asarray(loads, dtype=float))
    z = (x - x.mean()) / x.std()
    b0 = b1 = 0.0
    for _ in range(20_000):
        probability = 1.0 / (1.0 + np.exp(-(b0 + b1 * z)))
        b0 -= 0.1 * float((probability - y).mean())
        b1 -= 0.1 * float(((probability - y) * z).mean())
    return float(np.exp(x.mean() + x.std() * (-b0 / b1)))


def build_beta_summary(per_seed: pd.DataFrame) -> pd.DataFrame:
    """Resumo N=32 de Gini e J_beta, derivado da fonte canônica por seed."""
    metrics = ["jfi_slots", "gini_slots", *[f"j_beta_{beta:+.1f}" for beta in BETAS]]
    rows: list[dict[str, object]] = []
    for key, group in per_seed.loc[per_seed["carga"] == 32].groupby(
        ["pathloss", "alpha", "sched"], dropna=False
    ):
        pathloss, alpha, sched = key
        row = {"pathloss": pathloss, "alpha": alpha, "sched": sched, "carga": 32, "seed_count": len(group)}
        for metric in metrics:
            row[f"{metric}_mean"] = float(group[metric].mean())
            row[f"{metric}_std"] = float(group[metric].std(ddof=1))
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["pathloss", "alpha", "sched"], na_position="first")


def build_bootstrap_summary(per_seed: pd.DataFrame, repeats: int = 2000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """IC bootstrap de JFI por condição e cruzamento exploratório por cenário."""
    rng = np.random.default_rng(2026)
    rows: list[dict[str, object]] = []
    ld_rows: list[dict[str, object]] = []
    maxci = per_seed.loc[per_seed["sched"] == "MaxCI"]
    for key, scenario in maxci.groupby(["pathloss", "alpha"], dropna=False):
        pathloss, alpha = key
        label = scenario_label(pathloss, alpha)
        grouped = scenario.groupby("carga")["jfi_slots"]
        loads, means = [], []
        for carga, values in grouped:
            lo, hi = bootstrap_ci(values.to_numpy(), rng, repeats)
            mean = float(values.mean())
            rows.append({"cenario": label, "carga": int(carga), "jfi_slots_mean": mean,
                         "jfi_slots_bootstrap_lo": lo, "jfi_slots_bootstrap_hi": hi,
                         "seed_count": len(values), "injusto_mean(<0.5)": int(mean < 0.5)})
            loads.append(carga); means.append(mean)
        ld_rows.append({"cenario": label, "ld50_exploratory_carga": exploratory_ld50(np.array(loads), np.array(means)),
                        "n_cargas": len(loads), "nota": "cruzamento de médias; sem IC do LD50"})
    return pd.DataFrame(rows), pd.DataFrame(ld_rows)


def write_derived_outputs(per_seed: pd.DataFrame, out_dir: str) -> None:
    """Material derivado sem outro simulador ou outra população de seeds."""
    beta = build_beta_summary(per_seed)
    bootstrap, ld50 = build_bootstrap_summary(per_seed)
    beta.to_csv(os.path.join(out_dir, "estudo_robustez_beta.csv"), index=False)
    bootstrap.to_csv(os.path.join(out_dir, "estudo_bootstrap_ic.csv"), index=False)
    ld50.to_csv(os.path.join(out_dir, "estudo_ld50.csv"), index=False)
    print(f"saved derived analyses: beta={len(beta)} bootstrap={len(bootstrap)} ld50={len(ld50)}")




def pathloss_umi_nlos(distance_3d: np.ndarray, fc_hz: float = 3.5e9) -> np.ndarray:
    """Contraste UMi NLOS relativo, não link budget absoluto."""
    return 36.7 * np.log10(distance_3d) + 22.7 + 26.0 * np.log10(fc_hz / 1e9)


def build_umi_illustration(ttis: int = 10_000, radius_m: float = 500.0) -> pd.DataFrame:
    rows = []
    for carga in (2, 4, 8, 16, 32):
        seed = carga
        prng = np.random.default_rng(1000 + seed)
        radius = radius_m * np.sqrt(prng.uniform(0, 1, carga))
        theta = prng.uniform(0, 2 * np.pi, carga)
        distance_2d = np.maximum(radius, 1.0)
        distance_3d = np.sqrt(distance_2d**2 + (25 - 1.5)**2)
        pathloss_db = pathloss_umi_nlos(distance_3d)
        gamma = 10 ** (-pathloss_db / 10)
        gamma /= gamma.mean()
        realization = generate_channel(seed=seed, num_ues=carga, num_ttis=ttis)
        cfg = Config(num_ttis=ttis, num_seeds=1, user_counts=[carga])
        hetero_rates = compute_rates(cfg, np.abs(realization.h) * np.sqrt(gamma)[None, :])
        homogeneous_rates = compute_rates(cfg, np.abs(realization.h))
        hetero_alloc = run_seed(MaxCIScheduler, hetero_rates, carga)
        homogeneous_alloc = run_seed(MaxCIScheduler, homogeneous_rates, carga)
        rows.append({"carga": carga,
                     "jfi_homog_sem_pl": jains_fairness_index(np.bincount(homogeneous_alloc, minlength=carga)),
                     "jfi_UMi_NLOS": jains_fairness_index(np.bincount(hetero_alloc, minlength=carga)),
                     "pl_range_dB": f"{pathloss_db.min():.1f}~{pathloss_db.max():.1f}"})
    return pd.DataFrame(rows)


def build_hetero_illustration(ttis: int = 10_000, scale_snr: float = 4.0) -> pd.DataFrame:
    carga, seed = 8, 0
    realization = generate_channel(seed=seed, num_ues=carga, num_ttis=ttis)
    factor = np.ones(carga)
    factor[0] = np.sqrt(scale_snr)
    cfg = Config(num_ttis=ttis, num_seeds=1, user_counts=[carga])
    allocation = run_seed(MaxCIScheduler, compute_rates(cfg, np.abs(realization.h) * factor[None, :]), carga)
    return pd.DataFrame({"ue": np.arange(carga), "slots": np.bincount(allocation, minlength=carga)})


def write_illustrations(out_dir: str, ttis: int) -> None:
    build_umi_illustration(ttis).to_csv(os.path.join(out_dir, "estudo_umi_nlos.csv"), index=False)
    build_hetero_illustration(ttis).to_csv(os.path.join(out_dir, "estudo_hetero_4x.csv"), index=False)


def _scenario_name(pathloss: bool, alpha: float | None) -> str:
    return "homogêneo" if not pathloss else f"log-distance α={float(alpha):.1f}"


def export_figures(consolidated: pd.DataFrame, output_dir: str | os.PathLike[str]) -> None:
    """Figuras legíveis: facetas por cenário e séries limitadas por pergunta."""
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for stale in output.glob("*.png"):
        stale.unlink()

    scheduler_colors = {"RR": "#0072B2", "PF": "#009E73", "MaxCI": "#D55E00"}
    loads = sorted(consolidated["carga"].unique())
    representative = consolidated[(~consolidated["pathloss"]) | ((consolidated["pathloss"]) & (consolidated["alpha"] == 3.0))]
    panels = [(False, None, "Homogêneo"), (True, 3.0, "Log-distance α=3")]

    # Pergunta 1: mesmo scheduler, dois regimes, duas definições de justiça.
    figure, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True, sharey="row")
    for column, (pathloss, alpha, title) in enumerate(panels):
        panel = representative[(representative["pathloss"] == pathloss) & (representative["alpha"].isna() if alpha is None else representative["alpha"] == alpha)]
        for row, (metric, ci, ylabel) in enumerate((
            ("jfi_slots_mean", "jfi_slots_ci95", "JFI de slots"),
            ("jfi_throughput_mean", "jfi_throughput_ci95", "JFI de vazão"),
        )):
            axis = axes[row, column]
            for sched, group in panel.groupby("sched"):
                group = group.sort_values("carga")
                axis.plot(group["carga"], group[metric], marker="o", color=scheduler_colors[sched], label=sched)
                if ci in group:
                    axis.fill_between(group["carga"], group[metric]-group[ci], group[metric]+group[ci], color=scheduler_colors[sched], alpha=.12)
            axis.set_title(title if row == 0 else "")
            axis.set_xscale("log", base=2); axis.set_xticks(loads); axis.grid(alpha=.25)
            if column == 0: axis.set_ylabel(ylabel)
            if row == 1: axis.set_xlabel("Carga, UEs")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.suptitle("Justiça: regime homogêneo versus heterogeneidade representativa", y=.995)
    figure.legend(handles, labels, loc="upper center", bbox_to_anchor=(.5, .955), ncol=3, frameon=False)
    figure.tight_layout(rect=(0, 0, 1, .86))
    figure.savefig(output / "jfi_cenarios.png", dpi=180); plt.close(figure)

    # Pergunta 2: quanto o expoente de perda agrava apenas o MaxCI.
    maxci = consolidated[consolidated["sched"] == "MaxCI"]
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)
    alphas = sorted(maxci.loc[maxci["pathloss"], "alpha"].unique())
    alpha_colors = plt.cm.viridis(np.linspace(.15, .9, len(alphas)))
    for alpha, color in zip(alphas, alpha_colors, strict=True):
        group = maxci[(maxci["pathloss"]) & (maxci["alpha"] == alpha)].sort_values("carga")
        axes[0].plot(group["carga"], group["jfi_slots_mean"], marker="o", color=color, label=f"α={alpha:.1f}")
        axes[1].plot(group["carga"], group["gini_slots_mean"], marker="o", color=color, label=f"α={alpha:.1f}")
    for axis, title, ylabel in ((axes[0], "Justiça de tempo", "JFI de slots"), (axes[1], "Concentração", "Gini de slots")):
        axis.set_xscale("log", base=2); axis.set_xticks(loads); axis.set_xlabel("Carga, UEs"); axis.set_ylabel(ylabel); axis.set_title(title); axis.grid(alpha=.25)
    axes[1].legend(title="Path loss", fontsize=8)
    figure.suptitle("MaxCI: severidade da heterogeneidade", y=.99)
    figure.tight_layout()
    figure.savefig(output / "maxci_alpha.png", dpi=180); plt.close(figure)

    # Pergunta 3: o que acontece à borda e à exclusão, sem misturar schedulers.
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)
    for alpha, color in zip(alphas, alpha_colors, strict=True):
        group = maxci[(maxci["pathloss"]) & (maxci["alpha"] == alpha)].sort_values("carga")
        axes[0].plot(group["carga"], group["thr_5pct_mean"] / 1e6, marker="o", color=color, label=f"α={alpha:.1f}")
        axes[1].plot(group["carga"], group["nunca_mean"], marker="o", color=color, label=f"α={alpha:.1f}")
    for axis, title, ylabel in ((axes[0], "Vazão de borda", "5º percentil, Mbit/s"), (axes[1], "Exclusão", "UEs nunca atendidos, média")):
        axis.set_xscale("log", base=2); axis.set_xticks(loads); axis.set_xlabel("Carga, UEs"); axis.set_ylabel(ylabel); axis.set_title(title); axis.grid(alpha=.25)
    axes[1].legend(title="Path loss", fontsize=8)
    figure.suptitle("MaxCI: impacto sobre os UEs de borda", y=.99)
    figure.tight_layout()
    figure.savefig(output / "borda_exclusao.png", dpi=180); plt.close(figure)

    # Pergunta 4: comparação final entre políticas na maior carga disponível.
    n = max(loads)
    panel = representative[representative["carga"] == n]
    figure, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    names = ["RR", "PF", "MaxCI"]; x = np.arange(len(names)); width = .36
    for index, (pathloss, alpha, label) in enumerate(panels):
        group = panel[(panel["pathloss"] == pathloss) & (panel["alpha"].isna() if alpha is None else panel["alpha"] == alpha)].set_index("sched").reindex(names)
        axes[0].bar(x + (index-.5)*width, group["jfi_throughput_mean"], width, label=label)
        axes[1].bar(x + (index-.5)*width, group["throughput_aggregate_bps_mean"] / 1e6, width, label=label)
    for axis, title, ylabel in ((axes[0], f"Justiça de vazão, N={n}", "JFI de vazão"), (axes[1], f"Eficiência da célula, N={n}", "Vazão agregada, Mbit/s")):
        axis.set_xticks(x, names); axis.set_ylabel(ylabel); axis.set_title(title); axis.grid(axis="y", alpha=.25)
    axes[1].legend(fontsize=8)
    figure.suptitle("Trade-off entre políticas no maior nível de carga", y=.99)
    figure.tight_layout()
    figure.savefig(output / "tradeoff_n32.png", dpi=180); plt.close(figure)


    # Pergunta 5: o custo temporal que fica escondido pelo JFI agregado.
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), sharex=True)
    for pathloss, alpha, label in panels:
        panel = representative[(representative["pathloss"] == pathloss) & (representative["alpha"].isna() if alpha is None else representative["alpha"] == alpha)]
        for sched, group in panel.groupby("sched"):
            group = group.sort_values("carga")
            style = "-" if not pathloss else "--"
            axes[0].plot(group["carga"], group["jfi_win_mean"], style, marker="o", color=scheduler_colors[sched], label=f"{label} · {sched}")
            axes[1].plot(group["carga"], group["starv_max_mean"], style, marker="o", color=scheduler_colors[sched], label=f"{label} · {sched}")
    for axis, title, ylabel in ((axes[0], "Justiça em janela", "JFI por janela"), (axes[1], "Maior gap observado", "TTIs, escala log")):
        axis.set_xscale("log", base=2); axis.set_xticks(loads); axis.set_xlabel("Carga, UEs"); axis.set_ylabel(ylabel); axis.set_title(title); axis.grid(alpha=.25)
    axes[1].set_yscale("log")
    axes[1].legend(fontsize=7, ncol=2)
    figure.suptitle("Temporalidade: espera irregular sem e com heterogeneidade", y=.99)
    figure.tight_layout()
    figure.savefig(output / "temporalidade.png", dpi=180); plt.close(figure)

    # Pergunta 6: a conclusão persiste quando a definição de justiça muda?
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.5))
    panel = consolidated[(consolidated["carga"] == max(loads)) & (consolidated["pathloss"]) & (consolidated["alpha"] == 3.0)]
    beta_columns = [column for column in ("j_beta_-3.0_mean", "j_beta_-2.0_mean", "j_beta_-1.0_mean", "j_beta_+0.0_mean", "j_beta_+0.5_mean", "j_beta_+0.9_mean") if column in panel]
    beta_labels = [column.removeprefix("j_beta_").removesuffix("_mean") for column in beta_columns]
    for sched, group in panel.groupby("sched"):
        axes[0].plot(beta_labels, group.iloc[0][beta_columns].to_numpy(dtype=float), marker="o", color=scheduler_colors[sched], label=sched)
    axes[0].set_title("Família Jβ, N=32, α=3"); axes[0].set_xlabel("β"); axes[0].set_ylabel("Índice de justiça"); axes[0].set_ylim(0, 1.05); axes[0].grid(alpha=.25); axes[0].legend()
    order = ["RR", "PF", "MaxCI"]
    values = panel.set_index("sched").reindex(order)["gini_slots_mean"]
    axes[1].bar(order, values, color=[scheduler_colors[s] for s in order])
    axes[1].set_title("Gini de slots, N=32, α=3"); axes[1].set_ylabel("Concentração"); axes[1].set_ylim(0, 1.05); axes[1].grid(axis="y", alpha=.25)
    figure.suptitle("Robustez da conclusão à métrica de justiça", y=.99)
    figure.tight_layout()
    figure.savefig(output / "robustez_metricas.png", dpi=180); plt.close(figure)


    # Pergunta 7: eficiência por carga, separada do gráfico de ponto final.
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), sharey=True)
    for axis, (pathloss, alpha, label) in zip(axes, panels, strict=True):
        panel = representative[(representative["pathloss"] == pathloss) & (representative["alpha"].isna() if alpha is None else representative["alpha"] == alpha)]
        for sched, group in panel.groupby("sched"):
            group = group.sort_values("carga")
            y = group["throughput_aggregate_bps_mean"] / 1e6
            ci = group["throughput_aggregate_bps_ci95"] / 1e6
            axis.plot(group["carga"], y, marker="o", color=scheduler_colors[sched], label=sched)
            axis.fill_between(group["carga"], y-ci, y+ci, color=scheduler_colors[sched], alpha=.12)
        axis.set_xscale("log", base=2); axis.set_xticks(loads); axis.set_xlabel("Carga, UEs"); axis.set_title(label); axis.grid(alpha=.25)
    axes[0].set_ylabel("Vazão agregada, Mbit/s")
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", ncol=3, frameon=False)
    figure.suptitle("Eficiência da célula em função da carga", y=.99)
    figure.tight_layout(rect=(0, 0, 1, .91))
    figure.savefig(output / "eficiencia_carga.png", dpi=180); plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=50)
    parser.add_argument("--ttis", type=int, default=10_000)
    parser.add_argument("--out-dir", default="results")
    args = parser.parse_args()
    base = Config(num_ttis=args.ttis, num_seeds=args.seeds, user_counts=[2, 4, 8, 16, 32])
    per_seed, consolidated = build(base, seeds=args.seeds, ttis=args.ttis, out_dir=args.out_dir)
    write_derived_outputs(per_seed, args.out_dir)
    write_illustrations(args.out_dir, args.ttis)
    export_figures(consolidated, os.path.join(args.out_dir, "figuras"))


if __name__ == "__main__":
    main()
