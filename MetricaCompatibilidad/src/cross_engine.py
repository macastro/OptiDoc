"""
cross_engine.py — Comparación CROSS-ENGINE (motor de origen vs. LibreOffice).

El pipeline base (src/pipeline.py) compara LibreOffice consigo mismo para AISLAR
el mapeo de formato OOXML/.doc -> ODF. Por diseño, NO captura las diferencias
ENTRE motores (p. ej. Microsoft Word vs. LibreOffice): saltos de línea distintos,
reflujo, cambios de paginación, espaciado y sustitución de fuentes. Esa
diferencia entre motores es la pregunta central de compatibilidad del proyecto.

Este módulo la mide directamente:
    referencia = PDF exportado por la suite de ORIGEN (Word)   -- Se genera desde Word
    objetivo   = PDF que LibreOffice produce del MISMO documento -- Lo genera el script
    índice     = f(SSIM visual, conservación de paginación)      -- 0..100

Por qué se requiere un PDF de Word: Microsoft Word no está disponible en 
entorno Linux(solo hay LibreOffice), de modo que el render de referencia debe
generarse en Word (Archivo > Exportar > PDF) y aportarse como entrada. Esto no
es una limitación del método sino del entorno de ejecución.

Uso:
    python -m src.cross_engine --referencia word_09.pdf \
        --documento corpus/reunion_seguimiento/09_...doc --salida salidas_cross
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import conversion, metricas, puntaje, rasterizar  # noqa: E402

# En cross-engine el índice usa las dos dimensiones medibles desde el render.
# La dimensión de fuentes cross-engine requiere cotejar fuentes solicitadas
# contra las disponibles en cada motor y se aborda por separado (protocolo §4.4).
PESOS_CROSS = {"fidelidad_visual": 0.5, "conservacion_paginacion": 0.5}


def comparar(
    referencia_pdf: Path,
    documento: Path,
    salida_dir: Path,
    dpi: int = 150,
    etiqueta_ref: str = "Word (referencia)",
    etiqueta_obj: str = "LibreOffice",
) -> dict:
    """Compara el render de referencia (Word) contra el de LibreOffice."""
    referencia_pdf = Path(referencia_pdf)
    documento = Path(documento)
    trabajo = salida_dir / documento.stem
    trabajo.mkdir(parents=True, exist_ok=True)

    # Objetivo: cómo abre LibreOffice el MISMO documento de origen.
    objetivo_pdf = conversion.convertir(documento, "pdf", trabajo / "objetivo_libreoffice")

    # Rasterizado de ambos renders al mismo DPI.
    pag_ref = rasterizar.rasterizar(referencia_pdf, trabajo / "img_referencia", dpi=dpi)
    pag_obj = rasterizar.rasterizar(objetivo_pdf, trabajo / "img_objetivo", dpi=dpi)

    # Métrica visual sobre páginas representativas.
    indices = rasterizar.indices_representativos(max(len(pag_ref), len(pag_obj)))
    visual = metricas.ssim_paginas(pag_ref, pag_obj, indices)

    comp = {
        "fidelidad_visual": puntaje.componente_visual(visual["ssim_promedio"]),
        "conservacion_paginacion": puntaje.componente_paginacion(len(pag_ref), len(pag_obj)),
    }
    indice = puntaje.indice_compuesto(comp, PESOS_CROSS)

    # Figura de diferencias en la página más divergente.
    fig_rel = None
    evaluadas = [d for d in visual["detalle"] if d["ssim"] is not None]
    if evaluadas and pag_ref and pag_obj:
        peor = min(evaluadas, key=lambda d: d["ssim"])
        idx = peor["pagina"] - 1
        if idx < len(pag_ref) and idx < len(pag_obj):
            fig = trabajo / f"cross_diferencias_pag{peor['pagina']}.png"
            metricas.guardar_figura_diferencias(
                pag_ref[idx], pag_obj[idx], fig,
                titulo=f"{documento.name} · {etiqueta_ref} vs {etiqueta_obj} · pág {peor['pagina']}",
                etiqueta_a=etiqueta_ref, etiqueta_b=etiqueta_obj,
            )
            fig_rel = str(fig.relative_to(salida_dir))

    reporte = {
        "documento": documento.name,
        "tipo_comparacion": "cross-engine (Word vs LibreOffice)",
        "paginas": {etiqueta_ref: len(pag_ref), etiqueta_obj: len(pag_obj)},
        "metrica_visual": visual,
        "componentes": comp,
        "pesos": PESOS_CROSS,
        "indice_compatibilidad_cross_engine": indice,
        "figura_diferencias": fig_rel,
    }
    with open(trabajo / "reporte_cross_engine.json", "w", encoding="utf-8") as fh:
        json.dump(reporte, fh, ensure_ascii=False, indent=2)
    return reporte


def main() -> None:
    ap = argparse.ArgumentParser(description="Comparación cross-engine (Word vs LibreOffice).")
    ap.add_argument("--referencia", type=Path, required=True,
                    help="PDF de referencia exportado desde Word.")
    ap.add_argument("--documento", type=Path, required=True,
                    help="Documento original (.docx/.doc) que abrirá LibreOffice.")
    ap.add_argument("--salida", type=Path, default=Path("salidas_cross"))
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args()

    r = comparar(args.referencia, args.documento, args.salida, dpi=args.dpi)
    print(json.dumps({
        "documento": r["documento"],
        "paginas": r["paginas"],
        "ssim_promedio": r["metrica_visual"]["ssim_promedio"],
        "componentes": r["componentes"],
        "indice_cross_engine": r["indice_compatibilidad_cross_engine"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
