"""
metricas.py — Métrica visual de fidelidad (SSIM) entre origen y destino.

Dimensión "Divergencia visual de maquetación" de la Sección 5: se rasterizan
ambas versiones y se calcula el índice de similitud estructural (SSIM; Wang
et al., 2004) por página representativa. Valor 1.0 = idénticas; menor = mayor
divergencia. Incluye:
  - cálculo de SSIM por página y promedio,
  - una autoprueba que verifica que la métrica está bien implementada
    (SSIM(x,x)=1 y SSIM(x, x desplazada) < 1),
  - generación de una figura comparativa (origen | destino | mapa de diferencias).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from skimage.color import rgb2gray
from skimage.io import imread
from skimage.metrics import structural_similarity as ssim
from skimage.transform import resize

# Umbral provisional a partir del cual una página se considera "compatible"
# (se documentará/ajustará con datos; ver protocolo experimental).
UMBRAL_SSIM_COMPATIBLE = 0.99


def cargar_gris(ruta: str | Path) -> np.ndarray:
    """Carga una imagen y la devuelve en escala de grises, float en [0, 1]."""
    img = imread(str(ruta))
    if img.ndim == 3:
        img = rgb2gray(img[..., :3])
    img = img.astype(np.float64)
    if img.max() > 1.0:  # por si viniera en [0, 255]
        img = img / 255.0
    return img


def ssim_par(ruta_a: str | Path, ruta_b: str | Path) -> float:
    """SSIM entre dos imágenes. Redimensiona B a la forma de A si difieren."""
    a = cargar_gris(ruta_a)
    b = cargar_gris(ruta_b)
    if a.shape != b.shape:
        b = resize(b, a.shape, anti_aliasing=True)
    return float(ssim(a, b, data_range=1.0))


def ssim_paginas(
    paginas_origen: list[Path],
    paginas_destino: list[Path],
    indices: list[int],
) -> dict:
    """
    Calcula el SSIM en las páginas representativas (alineadas por índice).

    Devuelve un dict con el detalle por página y el promedio. Las páginas que
    existan en un lado pero no en el otro se marcan como faltantes (señal de
    cambio de paginación) y no entran en el promedio visual.
    """
    detalle = []
    valores = []
    for i in indices:
        if i < len(paginas_origen) and i < len(paginas_destino):
            v = ssim_par(paginas_origen[i], paginas_destino[i])
            valores.append(v)
            detalle.append(
                {
                    "pagina": i + 1,
                    "ssim": round(v, 4),
                    "compatible": v >= UMBRAL_SSIM_COMPATIBLE,
                }
            )
        else:
            detalle.append({"pagina": i + 1, "ssim": None, "compatible": False,
                            "nota": "página faltante (cambio de paginación)"})

    promedio = round(float(np.mean(valores)), 4) if valores else 0.0
    return {
        "ssim_promedio": promedio,
        "paginas_evaluadas": len(valores),
        "umbral_compatible": UMBRAL_SSIM_COMPATIBLE,
        "detalle": detalle,
    }


def autoprueba_ssim(ruta_imagen: str | Path) -> dict:
    """
    Verifica que la métrica está bien implementada y es sensible:
      - SSIM(x, x) debe ser 1.0
      - SSIM(x, x desplazada 5 px) debe ser < 1.0
    Devuelve los valores; sirve como test de cordura del pipeline.
    """
    x = cargar_gris(ruta_imagen)
    igual = float(ssim(x, x, data_range=1.0))
    desplazada = np.roll(x, 5, axis=0)
    distinta = float(ssim(x, desplazada, data_range=1.0))
    return {
        "ssim_identicas": round(igual, 4),
        "ssim_desplazada": round(distinta, 4),
        "implementacion_ok": igual > 0.999 and distinta < igual,
    }


def guardar_figura_diferencias(
    ruta_origen: str | Path,
    ruta_destino: str | Path,
    ruta_salida: str | Path,
    titulo: str = "",
    etiqueta_a: str = "Origen (.docx)",
    etiqueta_b: str = "Destino (.odt)",
) -> Path:
    """
    Guarda una figura de 3 paneles: origen, destino y mapa de diferencias
    absolutas, para inspeccionar visualmente dónde se pierde fidelidad.
    Las etiquetas de los dos primeros paneles son parametrizables (para
    reutilizar la figura tanto en la comparación base como en la cross-engine).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    a = cargar_gris(ruta_origen)
    b = cargar_gris(ruta_destino)
    if a.shape != b.shape:
        b = resize(b, a.shape, anti_aliasing=True)
    diff = np.abs(a - b)
    val = float(ssim(a, b, data_range=1.0))

    fig, ejes = plt.subplots(1, 3, figsize=(13, 6))
    ejes[0].imshow(a, cmap="gray"); ejes[0].set_title(etiqueta_a)
    ejes[1].imshow(b, cmap="gray"); ejes[1].set_title(etiqueta_b)
    im = ejes[2].imshow(diff, cmap="inferno", vmin=0, vmax=max(diff.max(), 1e-6))
    ejes[2].set_title(f"|Diferencia|  ·  SSIM={val:.4f}")
    for e in ejes:
        e.set_xticks([]); e.set_yticks([])
    fig.colorbar(im, ax=ejes[2], fraction=0.046, pad=0.04)
    if titulo:
        fig.suptitle(titulo, fontsize=13)
    fig.tight_layout()
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta_salida, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return ruta_salida
