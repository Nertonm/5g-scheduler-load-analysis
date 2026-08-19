"""Fingerprint do working tree do candidate.

Hash determinístico dos arquivos versionados relevantes do projeto, para que
o receipt experimental identifique a versão exata do candidate (não só o HEAD
git). Usado por scripts/write_manifest.py e por tests/test_contracts.py para
validator que o receipt não está vencido.
"""
import glob
import hashlib
import os

# arquivos considerados parte do candidate (para o fingerprint do receipt)
CANDIDATE_GLOBS = [
    "src/*.py",
    "scripts/*.py",
    "tests/*.py",
    "docs/*.md",
    "notebooks/*.ipynb",
    "results/*.csv",
    "results/figuras/*.png",
    "Makefile", "README.md", "requirements.txt",
]


def tree_fingerprint(repo):
    """SHA-256 do working tree do candidate (git-tracked + untracked relevantes)."""
    files = set()
    for pat in CANDIDATE_GLOBS:
        for p in glob.glob(os.path.join(repo, pat)):
            if os.path.isfile(p):
                files.add(p)
    files = sorted(files)
    h = hashlib.sha256()
    for p in files:
        rel = os.path.relpath(p, repo)
        h.update(rel.encode())
        h.update(b"\0")
        try:
            h.update(open(p, "rb").read())
        except Exception:
            pass
        h.update(b"\0")
    return h.hexdigest()
