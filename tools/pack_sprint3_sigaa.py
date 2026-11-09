#!/usr/bin/env python3
"""Gera ZIP(s) para entrega Sprint 3 no SIGAA."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"
FULL = "oficina-arena-sprint3"
LIGHT = "oficina-arena-sprint3-codigo-docs"
THRESHOLD_MB = 95
SKIP_DIRS = {".venv", ".git", ".cursor", "dist", "__pycache__"}
SKIP_FILES = {"_gen_pdfs_equipe.py", "pack_sprint3_sigaa.sh", "pack_sprint3_sigaa.py", "AGENTS.md"}


def should_skip(rel: Path, *, skip_assets: bool) -> bool:
    if set(rel.parts) & SKIP_DIRS:
        return True
    if rel.name in SKIP_FILES:
        return True
    if skip_assets and rel.parts and rel.parts[0] == "assets":
        return True
    return rel.suffix == ".pyc"


def copy_tree(dest: Path, *, skip_assets: bool) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if should_skip(rel, skip_assets=skip_assets):
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def make_zip(folder: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in folder.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=str(f.relative_to(OUT)))


def main() -> None:
    OUT.mkdir(exist_ok=True)
    full_dir, light_dir = OUT / FULL, OUT / LIGHT
    copy_tree(full_dir, skip_assets=False)
    copy_tree(light_dir, skip_assets=True)
    assets = light_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "LEIA-ME_ASSETS.txt").write_text(
        "Assets (NPZ, glTF, texturas, audio) nao incluidos neste ZIP.\n"
        "Baixe o repositorio completo:\n"
        "https://github.com/GabrielSTCC/oficina-arena-cg\n",
        encoding="utf-8",
    )
    full_zip, light_zip = OUT / f"{FULL}.zip", OUT / f"{LIGHT}.zip"
    # PDF entregavel tambem na raiz dos pacotes
    pdf = ROOT / "docs" / "SPRINT3_VERSAO_PREVIA.pdf"
    if pdf.is_file():
        for d in (full_dir, light_dir):
            shutil.copy2(pdf, d / pdf.name)
    make_zip(full_dir, full_zip)
    make_zip(light_dir, light_zip)
    full_mb = full_zip.stat().st_size / (1024 * 1024)
    light_mb = light_zip.stat().st_size / (1024 * 1024)
    print(f"FULL  {full_zip.name}  ({full_mb:.1f} MiB)")
    print(f"LIGHT {light_zip.name} ({light_mb:.1f} MiB)")
    if full_mb > THRESHOLD_MB:
        print(f"RECOMENDADO SIGAA: {light_zip}")
    else:
        print(f"RECOMENDADO SIGAA: {full_zip}")


if __name__ == "__main__":
    main()
