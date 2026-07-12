"""
Compara cómo renderiza un documento Word frente a cómo lo renderiza LibreOffice.

El pipeline principal (pipeline.py) convierte con LibreOffice y vuelve a renderizar
con LibreOffice — esto aísla el efecto del formato, pero no captura las diferencias
propias de cada motor: saltos de línea distintos, reflujo de texto, cambios de
paginación o sustituciones de fuentes. Esas diferencias son exactamente lo que
queremos medir aquí.

Cómo funciona:
    referencia = PDF que Word exportó del documento original (hay que generarlo a mano)
    objetivo   = PDF que LibreOffice genera del mismo documento
    índice     = combinación de similitud visual y conservación de páginas (0-100)

Por qué necesitamos el PDF de Word por separado: Word no corre en Linux, así
que el render de referencia tiene que generarse en Word y pasarlo como entrada.
No es una limitación del método, sino del entorno.

Uso:
    python -m src.cross_engine --referencia word_09.pdf \
        --documento corpus/reunion_seguimiento/09_...doc --salida salidas_cross
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import conversion, metricas, puntaje, rasterizar  # noqa: E402

# Aquí solo usamos visual y paginación porque ambas se miden directamente desde el render.
# Las fuentes cross-engine son más complejas de medir y se tratan en un módulo aparte.
PESOS_CROSS = {"fidelidad_visual": 0.5, "conservacion_paginacion": 0.5}


def comparar(
    referencia_pdf: Path,
    documento: Path,
    salida_dir: Path,
    dpi: int = 150,
    etiqueta_ref: str = "Word (referencia)",
    etiqueta_obj: str = "LibreOffice",
) -> dict:
    """Compara visualmente el PDF de Word con el que genera LibreOffice para el mismo documento."""
    referencia_pdf = Path(referencia_pdf)
    documento = Path(documento)
    trabajo = salida_dir / documento.stem
    trabajo.mkdir(parents=True, exist_ok=True)

    # Pedimos a LibreOffice que convierta el documento original a PDF.
    objetivo_pdf = conversion.convertir(documento, "pdf", trabajo / "objetivo_libreoffice")

    # Convertimos ambos PDFs a imágenes al mismo DPI para poder comparar píxeles.
    pag_ref = rasterizar.rasterizar(referencia_pdf, trabajo / "img_referencia", dpi=dpi)
    pag_obj = rasterizar.rasterizar(objetivo_pdf, trabajo / "img_objetivo", dpi=dpi)

    # Calculamos la similitud visual en las páginas más representativas.
    indices = rasterizar.indices_representativos(max(len(pag_ref), len(pag_obj)))
    visual = metricas.ssim_paginas(pag_ref, pag_obj, indices)

    comp = {
        "fidelidad_visual": puntaje.componente_visual(visual["ssim_promedio"]),
        "conservacion_paginacion": puntaje.componente_paginacion(len(pag_ref), len(pag_obj)),
    }
    indice = puntaje.indice_compuesto(comp, PESOS_CROSS)

    # Guardamos una imagen comparativa de la página donde se ven más diferencias.
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


def _emparejar(corpus: Path, referencias: Path | None):
    """Empareja cada original (.docx/.doc) con su PDF de Word por nombre base.

    El PDF de referencia se busca con el mismo nombre y extensión .pdf, en la
    carpeta de referencias si se indica, o en la misma carpeta del corpus.
    Devuelve (pares_emparejados, originales_sin_referencia).
    """
    ref_dir = referencias or corpus
    originales = sorted(set(corpus.glob("*.docx")) | set(corpus.glob("*.doc")))
    pares, sin_ref = [], []
    for doc in originales:
        ref = ref_dir / (doc.stem + ".pdf")
        if ref.exists():
            pares.append((doc, ref))
        else:
            sin_ref.append(doc)
    return pares, sin_ref


def main() -> None:
    ap = argparse.ArgumentParser(description="Comparación cross-engine (Word vs LibreOffice).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--corpus", type=Path,
                   help="Carpeta con los originales (.docx/.doc) y sus PDF de Word "
                        "(mismo nombre, extensión .pdf). Procesa todos por lote.")
    g.add_argument("--documento", type=Path,
                   help="Un documento original individual (usar junto con --referencia).")
    ap.add_argument("--referencia", type=Path,
                    help="PDF de Word para el modo individual (--documento).")
    ap.add_argument("--referencias", type=Path,
                    help="Carpeta con los PDF de Word, si están separados de los "
                         "originales (modo --corpus).")
    ap.add_argument("--salida", type=Path, default=Path("salidas_cross"))
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args()

    if args.documento:
        if not args.referencia:
            ap.error("--documento requiere --referencia (el PDF exportado desde Word).")
        pares = [(args.documento, args.referencia)]
    else:
        pares, sin_ref = _emparejar(args.corpus, args.referencias)
        for d in sin_ref:
            print(f"[aviso] se omite '{d.name}': falta su PDF de Word "
                  f"(se esperaba '{d.stem}.pdf')", file=sys.stderr)
        if not pares:
            ap.error("Ningún documento se emparejó con su PDF de Word. Verifica que "
                     "cada original tenga un .pdf con el mismo nombre base.")

    args.salida.mkdir(parents=True, exist_ok=True)
    reportes = []
    for doc, ref in pares:
        print(f"[cross-engine] {doc.name}  vs  {ref.name} ...")
        reportes.append(comparar(ref, doc, args.salida, dpi=args.dpi))

    # Resumen CSV consolidado
    with open(args.salida / "resumen_cross_engine.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["documento", "paginas_word", "paginas_libreoffice", "ssim_promedio",
                    "fidelidad_visual", "conservacion_paginacion", "indice_cross_engine"])
        for r in reportes:
            pg = list(r["paginas"].values())
            w.writerow([r["documento"], pg[0], pg[1],
                        r["metrica_visual"]["ssim_promedio"],
                        r["componentes"]["fidelidad_visual"],
                        r["componentes"]["conservacion_paginacion"],
                        r["indice_compatibilidad_cross_engine"]])

    # Tabla en consola
    print("\n" + "=" * 80)
    print(f"{'Documento':<40}{'SSIM':<10}{'Págs(W/LO)':<12}{'Índice 0-100':>14}")
    print("-" * 80)
    for r in reportes:
        pg = list(r["paginas"].values())
        doc = r["documento"] if len(r["documento"]) <= 39 else r["documento"][:36] + "..."
        print(f"{doc:<40}{r['metrica_visual']['ssim_promedio']:<10}"
              f"{f'{pg[0]}/{pg[1]}':<12}{r['indice_compatibilidad_cross_engine']:>14}")
    print("=" * 80)
    print(f"\nResultados en: {args.salida.resolve()}  ·  consolidado: resumen_cross_engine.csv")


if __name__ == "__main__":
    main()
