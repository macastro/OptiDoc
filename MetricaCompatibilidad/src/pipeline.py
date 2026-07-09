"""
Orquesta el análisis completo de compatibilidad para uno o varios documentos.

Cada documento pasa por estos pasos:
  1. Inventario previo     — ¿cuán complejo es antes de convertir?
  2. Conversión a ODF      — .doc/.docx -> .odt.
  3. Renderizado a PDF     — tanto del original como del convertido.
  4. Rasterizado a PNG     — una imagen por página en cada PDF.
  5. Similitud visual      — SSIM en páginas representativas.
  6. Índice 0-100          — compatibilidad global.
  7. Figura + reporte JSON — comparativa de la página con mayor divergencia.

Nota sobre archivos .doc: python-docx solo entiende OOXML, así que cuando el
documento es un .doc binario antiguo generamos una copia normalizada a .docx
solo para el inventario. La medición de fidelidad se hace siempre sobre el
original, y el reporte lo indica claramente.

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


def _es_legacy_doc(ruta: Path) -> bool:
    """Devuelve True si el archivo es un .doc binario antiguo (Word 97-2003), no un .docx moderno."""
    return ruta.suffix.lower() == ".doc"


def procesar_documento(ruta_entrada: Path, salida_dir: Path, dpi: int = 150) -> dict:
    """Ejecuta el pipeline completo sobre un documento y devuelve su reporte."""
    ruta_entrada = Path(ruta_entrada)
    trabajo = salida_dir / ruta_entrada.stem
    trabajo.mkdir(parents=True, exist_ok=True)

    legacy = _es_legacy_doc(ruta_entrada)

    # 1) Inventario de características del documento.
    #    python-docx no entiende el .doc antiguo, así que para esos archivos
    #    creamos una copia temporal en .docx solo para el inventario.
    #    La medición de fidelidad usa siempre el archivo original.
    if legacy:
        docx_inv = conversion.convertir(ruta_entrada, "docx", trabajo / "normalizado")
        inv = inventario.inventariar(docx_inv)
        inv["formato_original"] = ".doc (binario, Word 97-2003)"
        inv["inventario_derivado_de"] = (
            "copia normalizada a .docx con LibreOffice "
            "(python-docx no lee el binario .doc directamente)"
        )
        ruta_fuentes_decl = docx_inv
    else:
        inv = inventario.inventariar(ruta_entrada)
        inv["formato_original"] = ".docx (OOXML)"
        ruta_fuentes_decl = ruta_entrada

    # 2) Convertimos a ODF partiendo siempre del archivo original.
    odt = conversion.convertir(ruta_entrada, "odt", trabajo / "conversion")

    # 3) Renderizamos a PDF tanto el original como el convertido.
    pdf_origen = conversion.convertir(ruta_entrada, "pdf", trabajo / "render_origen")
    pdf_destino = conversion.convertir(odt, "pdf", trabajo / "render_destino")

    # 4) Convertimos cada PDF en imágenes PNG para poder comparar píxeles.
    pag_origen = rasterizar.rasterizar(pdf_origen, trabajo / "img_origen", dpi=dpi)
    pag_destino = rasterizar.rasterizar(pdf_destino, trabajo / "img_destino", dpi=dpi)

    # 5) Calculamos cuán parecidas se ven las páginas (SSIM).
    indices = rasterizar.indices_representativos(max(len(pag_origen), len(pag_destino)))
    visual = metricas.ssim_paginas(pag_origen, pag_destino, indices)

    # Usamos las fuentes que el autor eligió realmente, no las que Word declara por defecto.
    f_origen = set(inv.get("fuentes_usadas", []))
    f_destino = inventario.fuentes_odt(odt)

    # 6) Calculamos el índice de compatibilidad.
    score = puntaje.calcular(
        ssim_promedio=visual["ssim_promedio"],
        paginas_origen=len(pag_origen),
        paginas_destino=len(pag_destino),
        fuentes_origen=f_origen,
        fuentes_destino=f_destino,
        sustituciones=inventario.SUSTITUCIONES_SEGURAS,
    )

    # 7) Guardamos una imagen comparativa de la página con más diferencias.
    fig_rel = None
    evaluadas = [d for d in visual["detalle"] if d["ssim"] is not None]
    if evaluadas and pag_origen and pag_destino:
        peor = min(evaluadas, key=lambda d: d["ssim"])
        idx = peor["pagina"] - 1
        if idx < len(pag_origen) and idx < len(pag_destino):
            fig = trabajo / f"diferencias_pag{peor['pagina']}.png"
            metricas.guardar_figura_diferencias(
                pag_origen[idx], pag_destino[idx], fig,
                titulo=f"{ruta_entrada.name} · página {peor['pagina']}",
            )
            fig_rel = str(fig.relative_to(salida_dir))

    reporte = {
        "documento": ruta_entrada.name,
        "formato_original": inv["formato_original"],
        "prediccion_previa": inv,
        "paginas": {"origen": len(pag_origen), "destino": len(pag_destino)},
        "fuentes": {
            "declaradas_origen": sorted(inventario.fuentes_docx(ruta_fuentes_decl)),
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
    print("\n" + "=" * 92)
    print(f"{'Documento':<34}{'Formato':<12}{'Complej.':<10}"
          f"{'SSIM':<8}{'Págs':<8}{'Índice 0-100':>14}")
    print("-" * 92)
    for r in reportes:
        comp = r["prediccion_previa"]["complejidad"]
        ssim_p = r["metrica_visual"]["ssim_promedio"]
        pag = f"{r['paginas']['origen']}/{r['paginas']['destino']}"
        idx = r["puntaje"]["indice_compatibilidad"]
        fmt = "doc→norm" if r["formato_original"].startswith(".doc ") else "docx"
        doc = r["documento"] if len(r["documento"]) <= 33 else r["documento"][:30] + "..."
        print(f"{doc:<34}{fmt:<12}{comp:<10}{ssim_p:<8}{pag:<8}{idx:>14}")
    print("=" * 92 + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Pipeline básico de compatibilidad (Hito 1).")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--corpus", type=Path, help="Carpeta con documentos .docx/.doc.")
    g.add_argument("--doc", type=Path, help="Un documento .docx/.doc individual.")
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
        # Buscamos tanto .docx modernos como los viejos .doc binarios.
        docs = sorted(
            set(args.corpus.glob("*.docx")) | set(args.corpus.glob("*.doc"))
        )
        if not docs:
            print(f"No se encontraron .docx/.doc en {args.corpus}", file=sys.stderr)
            sys.exit(1)

    reportes = []
    for d in docs:
        print(f"[procesando] {d.name} ...")
        reportes.append(procesar_documento(d, args.salida, dpi=args.dpi))

    # Exportamos un CSV con el resumen de todos los documentos procesados.
    with open(args.salida / "resumen.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["documento", "formato_original", "complejidad", "esfuerzo_previsto",
                    "ssim_promedio", "paginas_origen", "paginas_destino",
                    "fidelidad_visual", "conservacion_paginacion",
                    "conservacion_fuentes", "indice_compatibilidad"])
        for r in reportes:
            c = r["puntaje"]["componentes"]
            w.writerow([
                r["documento"], r["formato_original"],
                r["prediccion_previa"]["complejidad"],
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
