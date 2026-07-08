"""
pipeline.py — Orquestador del pipeline básico de compatibilidad (Hito 1).

Para cada documento .docx:
  1. Inventario de características (predicción previa).
  2. Conversión OOXML -> ODF (docx -> odt).
  3. Render de origen (docx -> pdf) y destino (odt -> pdf) con LibreOffice.
  4. Rasterizado de ambos a PNG por página.
  5. Métrica visual SSIM sobre páginas representativas.
  6. Índice de compatibilidad provisional (0-100).
  7. Figura de diferencias de la página más divergente + reporte JSON.

Uso:
    python -m src.pipeline --corpus corpus/sinteticos --salida salidas
    python -m src.pipeline --doc ruta/al/documento.docx --salida salidas
    python -m src.pipeline --autotest corpus/sinteticos/<algun>.docx
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Permite ejecutar como módulo (python -m src.pipeline) o como script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import conversion, inventario, metricas, puntaje, rasterizar  # noqa: E402


def procesar_documento(ruta_docx: Path, salida_dir: Path, dpi: int = 150) -> dict:
    """Ejecuta el pipeline completo sobre un documento y devuelve su reporte."""
    ruta_docx = Path(ruta_docx)
    trabajo = salida_dir / ruta_docx.stem
    trabajo.mkdir(parents=True, exist_ok=True)

    # 1) Predicción previa
    inv = inventario.inventariar(ruta_docx)

    # 2) Conversión de formato OOXML -> ODF
    odt = conversion.convertir(ruta_docx, "odt", trabajo / "conversion")

    # 3) Render origen y destino (carpetas separadas: mismo basename)
    pdf_origen = conversion.convertir(ruta_docx, "pdf", trabajo / "render_origen")
    pdf_destino = conversion.convertir(odt, "pdf", trabajo / "render_destino")

    # 4) Rasterizado
    pag_origen = rasterizar.rasterizar(pdf_origen, trabajo / "img_origen", dpi=dpi)
    pag_destino = rasterizar.rasterizar(pdf_destino, trabajo / "img_destino", dpi=dpi)

    # 5) Métrica visual
    indices = rasterizar.indices_representativos(max(len(pag_origen), len(pag_destino)))
    visual = metricas.ssim_paginas(pag_origen, pag_destino, indices)

    # Dimensión de fuentes. El PUNTAJE se basa en las fuentes EFECTIVAMENTE
    # USADAS por los runs (señal limpia), no en las declaradas (que incluyen
    # defaults de la suite no elegidos por el autor). Se conserva el mapa de
    # sustituciones seguras para dar crédito a reemplazos métricamente compatibles.
    f_origen = set(inv.get("fuentes_usadas", []))
    f_destino = inventario.fuentes_odt(odt)

    # 6) Índice compuesto provisional
    score = puntaje.calcular(
        ssim_promedio=visual["ssim_promedio"],
        paginas_origen=len(pag_origen),
        paginas_destino=len(pag_destino),
        fuentes_origen=f_origen,
        fuentes_destino=f_destino,
        sustituciones=inventario.SUSTITUCIONES_SEGURAS,
    )

    # 7) Figura de diferencias: página representativa con menor SSIM
    fig_rel = None
    evaluadas = [d for d in visual["detalle"] if d["ssim"] is not None]
    if evaluadas and pag_origen and pag_destino:
        peor = min(evaluadas, key=lambda d: d["ssim"])
        idx = peor["pagina"] - 1
        if idx < len(pag_origen) and idx < len(pag_destino):
            fig = trabajo / f"diferencias_pag{peor['pagina']}.png"
            metricas.guardar_figura_diferencias(
                pag_origen[idx], pag_destino[idx], fig,
                titulo=f"{ruta_docx.name} · página {peor['pagina']}",
            )
            fig_rel = str(fig.relative_to(salida_dir))

    reporte = {
        "documento": ruta_docx.name,
        "prediccion_previa": inv,
        "paginas": {"origen": len(pag_origen), "destino": len(pag_destino)},
        "fuentes": {
            "declaradas_origen": sorted(inventario.fuentes_docx(ruta_docx)),
            "usadas_origen": inv.get("fuentes_usadas", []),
            "relevantes_origen": sorted(f_origen),
            "declaradas_destino": sorted(f_destino),
        },
        "metrica_visual": visual,
        "puntaje": score,
        "figura_diferencias": fig_rel,
    }

    with open(trabajo / "reporte.json", "w", encoding="utf-8") as fh:
        json.dump(reporte, fh, ensure_ascii=False, indent=2)
    return reporte


def _imprimir_tabla(reportes: list[dict]) -> None:
    print("\n" + "=" * 78)
    print(f"{'Documento':<28}{'Complej.':<10}{'SSIM':<8}{'Págs':<8}{'Índice 0-100':>14}")
    print("-" * 78)
    for r in reportes:
        comp = r["prediccion_previa"]["complejidad"]
        ssim_p = r["metrica_visual"]["ssim_promedio"]
        pag = f"{r['paginas']['origen']}/{r['paginas']['destino']}"
        idx = r["puntaje"]["indice_compatibilidad"]
        print(f"{r['documento']:<28}{comp:<10}{ssim_p:<8}{pag:<8}{idx:>14}")
    print("=" * 78 + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Pipeline básico de compatibilidad (Hito 1).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--corpus", type=Path, help="Carpeta con documentos .docx.")
    g.add_argument("--doc", type=Path, help="Un documento .docx individual.")
    g.add_argument("--autotest", type=Path, help="Imagen PNG para autoprueba de SSIM.")
    ap.add_argument("--salida", type=Path, default=Path("salidas"))
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args()

    if args.autotest:
        print(json.dumps(metricas.autoprueba_ssim(args.autotest), indent=2))
        return

    args.salida.mkdir(parents=True, exist_ok=True)

    if args.doc:
        docs = [args.doc]
    else:
        docs = sorted(args.corpus.glob("*.docx"))
        if not docs:
            print(f"No se encontraron .docx en {args.corpus}", file=sys.stderr)
            sys.exit(1)

    reportes = []
    for d in docs:
        print(f"[procesando] {d.name} ...")
        reportes.append(procesar_documento(d, args.salida, dpi=args.dpi))

    # Resumen CSV global
    with open(args.salida / "resumen.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["documento", "complejidad", "esfuerzo_previsto", "ssim_promedio",
                    "paginas_origen", "paginas_destino", "fidelidad_visual",
                    "conservacion_paginacion", "conservacion_fuentes",
                    "indice_compatibilidad"])
        for r in reportes:
            c = r["puntaje"]["componentes"]
            w.writerow([
                r["documento"], r["prediccion_previa"]["complejidad"],
                r["prediccion_previa"]["esfuerzo_previsto"],
                r["metrica_visual"]["ssim_promedio"],
                r["paginas"]["origen"], r["paginas"]["destino"],
                c["fidelidad_visual"], c["conservacion_paginacion"],
                c["conservacion_fuentes"], r["puntaje"]["indice_compatibilidad"],
            ])

    _imprimir_tabla(reportes)
    print(f"Reportes y figuras en: {args.salida.resolve()}")


if __name__ == "__main__":
    main()
