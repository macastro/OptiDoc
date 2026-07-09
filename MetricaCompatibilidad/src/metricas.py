"""
Mide qué tan parecidas se ven dos versiones de un documento comparando sus páginas
como imágenes. Usamos el índice SSIM (similitud estructural): vale 1.0 si son
idénticas y baja cuanto más divergen visualmente.

Incluye:
  - comparación página a página y cálculo del promedio,
  - una autoprueba para confirmar que el cálculo está bien (una imagen consigo
    misma debe dar 1.0; con una versión desplazada debe dar menos),
  - generación de una figura con tres paneles: original, convertido y mapa de
    diferencias para ver exactamente dónde cambiaron las cosas.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from skimage.color import rgb2gray
from skimage.io import imread
from skimage.metrics import structural_similarity as ssim
from skimage.transform import resize

# Por encima de este valor consideramos que una página se convirtió bien. Ajustar con datos reales.
UMBRAL_SSIM_COMPATIBLE = 0.99


def cargar_gris(ruta: str | Path) -> np.ndarray:
    """Carga una imagen y la devuelve en escala de grises, float en [0, 1]."""
    img = imread(str(ruta))
    if img.ndim == 3:
        img = rgb2gray(img[..., :3])
    img = img.astype(np.float64)
    if img.max() > 1.0:  # algunas imágenes vienen en rango 0-255; las normalizamos a 0-1
        img = img / 255.0
    return img


def ssim_par(ruta_a: str | Path, ruta_b: str | Path) -> float:
    """Calcula el SSIM entre dos imágenes. Si tienen distinto tamaño, ajusta la segunda a la primera."""
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
    Calcula el SSIM para las páginas representativas y devuelve el detalle por
    página junto con el promedio.

    Si una página existe en el original pero no en el convertido (o viceversa),
    la marcamos como faltante — eso indica un cambio en el número de páginas —
    y no la incluimos en el promedio visual.
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
    Comprueba que el cálculo de SSIM funciona correctamente:
      - Una imagen comparada consigo misma debe dar 1.0.
      - La misma imagen desplazada 5 píxeles debe dar un valor menor.
    Útil para confirmar que el entorno está bien configurado antes de procesar documentos.
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
    Genera una imagen con tres paneles: el original, el convertido y un mapa de calor
    que muestra dónde difieren. Sirve para ver de un vistazo dónde se perdió fidelidad.
    Las etiquetas son configurables para reutilizar la función en comparaciones cross-engine.
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
