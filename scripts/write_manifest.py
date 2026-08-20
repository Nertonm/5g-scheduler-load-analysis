"""Gera receipt dos artefatos canônicos do estudo pareado."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import subprocess
import sys

for candidate in (os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
    if os.path.isdir(os.path.join(candidate, "src")) and candidate not in sys.path:
        sys.path.insert(0, candidate)
        break

from src.fingerprint import tree_fingerprint


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(repo: str) -> str:
    result = subprocess.run(["git", "-c", f"safe.directory={repo}", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, timeout=10)
    return result.stdout.strip() if result.returncode == 0 else ""


PROTOCOLS = {
    "estudo_per_seed.csv": {
        "role": "fonte de verdade",
        "corrida": "50 seeds pareadas por scheduler, carga e cenário",
        "cenarios": "homogêneo e log-distance alpha=1.5,2.0,2.5,3.0,3.5,4.0",
        "cargas": [2, 4, 8, 16, 32],
        "num_ttis": 10000,
        "metricas": "JFI slots/vazão/janela, Gini slots/vazão, J_beta, gaps observados, vazão p5, nunca, vetores por UE",
    },
    "estudo_consolidado.csv": {
        "role": "resumo canônico",
        "fonte": "estudo_per_seed.csv",
        "agregacao": "média, DP amostral e IC95 normal para cada métrica por scheduler/carga/cenário",
    },
    "estudo_robustez_beta.csv": {
        "role": "visão de robustez",
        "fonte": "colunas j_beta_* de estudo_per_seed.csv, N=32",
        "betas": [-3.0, -2.0, -1.0, 0.0, 0.5, 0.9],
        "nota": "J_beta é calculado por seed antes da média; beta=-1 recupera Jain.",
    },
    "estudo_bootstrap_ic.csv": {
        "role": "IC bootstrap por condição",
        "fonte": "estudo_per_seed.csv",
        "metodo": "B=2000, percentil 2.5-97.5 para a média de JFI slots do MaxCI",
    },
    "estudo_ld50.csv": {
        "role": "exploratório",
        "fonte": "estudo_per_seed.csv",
        "nota": "cruzamento exploratório sem IC; não é LD50 inferencial até bootstrap do estimador no nível seed",
    },
    "estudo_umi_nlos.csv": {
        "role": "ilustrativo",
        "corrida": "uma seed de posição por carga, não média",
        "nota": "contraste de heterogeneidade relativa, não link budget UMi completo",
    },
    "estudo_hetero_4x.csv": {
        "role": "ilustrativo",
        "corrida": "seed 0, N=8",
        "nota": "UE0 com amplitude 2x, portanto potência/SNR 4x",
    },
}

CANONICAL_FILES = tuple(PROTOCOLS)


def main() -> None:
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results = os.path.join(repo, "results")
    files: dict[str, dict[str, object]] = {}
    for name in CANONICAL_FILES:
        path = os.path.join(results, name)
        entry: dict[str, object] = {"protocolo": PROTOCOLS[name]}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                entry["rows_dados"] = max(sum(1 for _ in handle) - 1, 0)
            entry["sha256"] = sha256(path)
            entry["bytes"] = os.path.getsize(path)
        else:
            entry["error"] = "nao encontrado"
        files[name] = entry

    figures = {}
    figures_dir = os.path.join(results, "figuras")
    if os.path.isdir(figures_dir):
        for name in sorted(os.listdir(figures_dir)):
            if name.endswith(".png"):
                path = os.path.join(figures_dir, name)
                figures[f"figuras/{name}"] = {"sha256": sha256(path), "bytes": os.path.getsize(path)}

    receipt = {
        "projeto": "5g-scheduler-load-analysis",
        "receipt_gerado_por": "scripts/write_manifest.py",
        "git_commit": git_commit(repo),
        "tree_fingerprint": tree_fingerprint(repo),
        "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "files": files,
        "figures": figures,
    }
    output = os.path.join(results, "manifest-estudos.json")
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=False)
    print(f"saved {output}")
    for name, entry in files.items():
        print(f"{name}: {entry.get('rows_dados', '?')} rows")


if __name__ == "__main__":
    main()
