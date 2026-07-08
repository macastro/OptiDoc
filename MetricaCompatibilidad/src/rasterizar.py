"""
rasterizar.py — Convierte un PDF a una imagen PNG por página (Poppler/pdftoppm).

Es el insumo para la métrica visual: se rasterizan origen y destino a la misma
resolución para poder compararlos píxel a píxel con SSIM (Sección 5 del plan).
"""
from __future__ import annotations

import glob
import shutil
import subprocess
from pathlib import Path


def _localizar_pdftoppm() -> str:
    ruta = shutil.which("pdftoppm")
    if not ruta:
        raise RuntimeError(
            "No se encontró 'pdftoppm' (paquete Poppler). Instálalo para rasterizar."
        )
    return ruta


def rasterizar(
    pdf: str | Path,
    salida_dir: str | Path,
    dpi: int = 150,
    prefijo: str = "pag",
) -> list[Path]:
    """
    Rasteriza `pdf` a PNG (una imagen por página) en `salida_dir`.

    Devuelve la lista de rutas de página ordenadas (pag-1.png, pag-2.png, ...).
    """
    pdf = Path(pdf).resolve()
    salida_dir = Path(salida_dir).resolve()
    salida_dir.mkdir(parents=True, exist_ok=True)
    base = str(salida_dir / prefijo)

    pdftoppm = _localizar_pdftoppm()
    cmd = [pdftoppm, "-png", "-r", str(dpi), str(pdf), base]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Falló pdftoppm sobre {pdf.name}: {proc.stderr}")

    paginas = sorted(glob.glob(base + "*.png"))
    if not paginas:
        raise RuntimeError(f"No se generaron imágenes a partir de {pdf.name}.")
    return [Path(p) for p in paginas]


def indices_representativos(n_paginas: int) -> list[int]:
    """
    Índices (base 0) de las páginas representativas: primera, intermedia y última
    (Sección 5: el SSIM se calcula sobre un conjunto acotado de páginas).
    """
    if n_paginas <= 0:
        return []
    if n_paginas == 1:
        return [0]
    if n_paginas == 2:
        return [0, 1]
    return sorted({0, n_paginas // 2, n_paginas - 1})
