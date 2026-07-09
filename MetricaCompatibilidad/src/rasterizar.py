"""
Convierte un PDF a imágenes PNG, una por página, usando Poppler (pdftoppm).

Antes de comparar dos documentos visualmente, ambos se rasterizan a la misma
resolución — así el cálculo de similitud (SSIM) puede trabajar píxel a píxel.
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
    Convierte cada página del PDF a una imagen PNG en la carpeta indicada.

    Devuelve las rutas ordenadas de las imágenes generadas (pag-1.png, pag-2.png, ...).
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
    Devuelve índices (base 0) de las páginas más representativas: la primera, la
    del medio y la última. Calcular el SSIM en todo el documento sería costoso;
    con estas tres se obtiene una lectura equilibrada sin procesar cada hoja.
    """
    if n_paginas <= 0:
        return []
    if n_paginas == 1:
        return [0]
    if n_paginas == 2:
        return [0, 1]
    return sorted({0, n_paginas // 2, n_paginas - 1})
