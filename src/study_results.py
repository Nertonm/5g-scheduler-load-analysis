"""Contrato canônico dos estudos pareados de escalonamento.

O dado autoritativo é uma linha por (scheduler, carga, cenário, seed). Os
resumos são derivados dessa tabela para impedir que estudos sem/com path loss
usem seeds ou métricas diferentes.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

KEY_COLUMNS = ("sched", "carga", "pathloss", "alpha", "seed")
GROUP_COLUMNS = ("sched", "carga", "pathloss", "alpha")
VECTOR_COLUMNS = {"slots_vec", "thr_vec"}


def scalar_metric_columns(frame: pd.DataFrame) -> list[str]:
    """Retorna métricas numéricas, excluindo chaves e vetores serializados."""
    excluded = set(KEY_COLUMNS) | VECTOR_COLUMNS
    return [
        column
        for column in frame.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(frame[column])
    ]


def validate_paired_seed_sets(frame: pd.DataFrame) -> list[str]:
    """Verifica que cada braço com path loss usa as mesmas seeds do braço base."""
    required = set(KEY_COLUMNS)
    missing = sorted(required - set(frame.columns))
    if missing:
        return [f"colunas obrigatorias ausentes: {', '.join(missing)}"]

    errors: list[str] = []
    for (sched, carga), group in frame.groupby(["sched", "carga"], dropna=False):
        baseline = set(group.loc[~group["pathloss"], "seed"])
        for alpha, arm in group.loc[group["pathloss"]].groupby("alpha", dropna=False):
            paired = set(arm["seed"])
            if baseline != paired:
                errors.append(
                    f"sched={sched} carga={carga} alpha={alpha}: "
                    f"seeds sem_pathloss={sorted(baseline)} com_pathloss={sorted(paired)}"
                )
    return errors


def aggregate_per_seed(frame: pd.DataFrame, z_critical: float = 1.96) -> pd.DataFrame:
    """Resume todas as métricas por cenário com média, DP, IC95 e número de seeds."""
    errors = validate_paired_seed_sets(frame)
    if errors:
        raise ValueError("; ".join(errors))

    metrics = scalar_metric_columns(frame)
    if not metrics:
        raise ValueError("nenhuma metrica numerica para agregar")

    rows: list[dict[str, object]] = []
    for key, group in frame.groupby(list(GROUP_COLUMNS), dropna=False):
        row = dict(zip(GROUP_COLUMNS, key, strict=True))
        n = len(group)
        row["seed_count"] = n
        for metric in metrics:
            values = group[metric].to_numpy(dtype=float)
            row[f"{metric}_mean"] = float(np.mean(values))
            row[f"{metric}_std"] = float(np.std(values, ddof=1)) if n > 1 else float("nan")
            row[f"{metric}_ci95"] = (
                float(z_critical * np.std(values, ddof=1) / np.sqrt(n))
                if n > 1
                else float("nan")
            )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(list(GROUP_COLUMNS), na_position="first").reset_index(drop=True)


def require_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    """Falha cedo se o consumidor receber esquema incompleto."""
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"colunas obrigatorias ausentes: {', '.join(missing)}")
