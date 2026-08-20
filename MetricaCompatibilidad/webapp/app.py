"""
app.py — Aplicación web para medir la compatibilidad de un documento.

Sube un documento de Word junto con su PDF exportado desde Word, y calcula el
índice de compatibilidad cross-engine (Word ↔ LibreOffice) con las cinco
métricas congeladas del Hito 2.

La app se adapta al entorno:
  * Con LibreOffice → acepta el .docx y lo renderiza en el servidor.
  * Sin LibreOffice (p. ej. hosting compartido) → acepta los dos PDF ya
    generados (el de Word y el de LibreOffice) y los compara.

Arranque en local:      python app.py
Producción (VPS):       gunicorn -w 2 -b 127.0.0.1:8000 app:app
Passenger (compartido): exponer 'application' (ver README_DESPLIEGUE.md).
"""
from __future__ import annotations

import base64
import tempfile
import traceback
from pathlib import Path

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

import motor

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024  # 30 MB por subida

CAPS = motor.capacidades()

DIMENSIONES = [
    ("fidelidad_visual", "Fidelidad visual", "Similitud de la maquetación (SSIM)"),
    ("conservacion_paginacion", "Conservación de paginación", "Mismo número de páginas"),
    ("conservacion_fuentes", "Conservación de fuentes", "Sustitución tipográfica entre motores"),
    ("estabilidad_flujo", "Estabilidad del flujo", "Reflujo: dónde caen los saltos de línea"),
    ("integridad_objetos", "Integridad de objetos", "Imágenes y objetos renderizados"),
]

EXT_DOC = {".docx", ".doc", ".odt", ".rtf"}


def _guardar(archivo, carpeta: Path) -> Path | None:
    """Guarda un archivo subido con nombre seguro. Devuelve None si está vacío."""
    if not archivo or not archivo.filename:
        return None
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = secure_filename(archivo.filename) or "archivo"
    destino = carpeta / nombre
    archivo.save(destino)
    return destino if destino.stat().st_size > 0 else None


def _es_pdf(ruta: Path) -> bool:
    return ruta.suffix.lower() == ".pdf"


def _construir_resultado(datos: dict, doc_nombre: str) -> dict:
    """Prepara el diccionario que consume la plantilla de resultado."""
    comp = datos["componentes"]
    dims = []
    for clave, titulo, desc in DIMENSIONES:
        if clave in comp:
            dims.append({
                "titulo": titulo, "descripcion": desc,
                "valor": comp[clave], "peso": int(motor.PESOS[clave] * 100),
            })
    figura = None
    png = motor.figura_diferencias(*datos["figura_paginas"])
    if png:
        figura = "data:image/png;base64," + base64.b64encode(png).decode("ascii")

    return {
        "documento": doc_nombre,
        "modo": datos["modo"],
        "indice": datos["indice"],
        "clasificacion": datos["clasificacion"],
        "problematico": datos["problematico"],
        "ssim": datos.get("ssim_promedio"),
        "paginas": datos["paginas"],
        "dimensiones": dims,
        "fuentes": datos.get("fuentes"),
        "objetos": datos.get("objetos"),
        "figura": figura,
    }


@app.route("/")
def inicio():
    return render_template("index.html", caps=CAPS, tab="uno",
                           version=motor.VERSION_METRICAS)


def _evaluar_documento(doc: Path, work: Path, pdf_word: Path | None = None,
                       pdf_lo: Path | None = None) -> dict:
    """Evalúa un documento y devuelve los datos de la métrica (o lanza RuntimeError).

    Genera el objetivo con LibreOffice y la referencia con Word cuando están
    disponibles; si no, usa los PDF que se le pasen. Sin referencia de Word cae
    al diagnóstico de mapeo a ODF.
    """
    obj_pdf = None
    if CAPS["libreoffice"]:
        obj_pdf = motor.convertir(doc, "pdf", work / "obj")
    elif pdf_lo and _es_pdf(pdf_lo):
        obj_pdf = pdf_lo

    ref_pdf = None
    if CAPS["word"]:
        ref_pdf = motor.convertir_con_word(doc, work / "ref")
    elif pdf_word and _es_pdf(pdf_word):
        ref_pdf = pdf_word

    if ref_pdf and obj_pdf:
        return motor.metricas_cross(ref_pdf, obj_pdf)
    if obj_pdf and not ref_pdf:
        if CAPS["libreoffice"]:
            odt = motor.convertir(doc, "odt", work / "odt")
            odt_pdf = motor.convertir(odt, "pdf", work / "odtpdf")
            return motor.metricas_mapeo(obj_pdf, odt_pdf)
        raise RuntimeError("Falta la referencia de Word (sube también su PDF exportado desde Word).")
    if ref_pdf and not obj_pdf:
        raise RuntimeError("Falta la versión de LibreOffice (instala LibreOffice o sube su PDF).")
    raise RuntimeError("Este servidor no puede convertir el documento; sube los PDF ya generados.")


@app.route("/analizar", methods=["POST"])
def analizar():
    """Modo de un documento."""
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        try:
            doc = _guardar(request.files.get("documento"), carpeta)
            pdf_word = _guardar(request.files.get("pdf_word"), carpeta)
            pdf_lo = _guardar(request.files.get("pdf_libreoffice"), carpeta)

            # --- Ruta A: dos PDF (funciona sin LibreOffice) ---
            if pdf_word and pdf_lo:
                if not _es_pdf(pdf_word) or not _es_pdf(pdf_lo):
                    return _error("Ambos archivos deben ser PDF.")
                datos = motor.metricas_cross(pdf_word, pdf_lo)
                return _ok(datos, pdf_word.stem)

            # --- Ruta B: documento ---
            if doc:
                if _es_pdf(doc):
                    return _error("Subiste un PDF en la casilla del documento. "
                                  "Usa las casillas de PDF, o sube el .docx aquí.")
                if doc.suffix.lower() not in EXT_DOC:
                    return _error(f"Formato no admitido: {doc.suffix}. "
                                  "Usa .docx, .doc, .odt o .rtf.")
                datos = _evaluar_documento(doc, carpeta, pdf_word=pdf_word, pdf_lo=pdf_lo)
                return _ok(datos, doc.name)

            return _error("No subiste ningún archivo. Elige un documento (o dos PDF).")

        except RuntimeError as exc:
            return _error(_mensaje_error(str(exc)))
        except Exception:                                       # noqa: BLE001
            traceback.print_exc()
            return _error("Ocurrió un error al procesar el archivo. Verifica que no esté "
                          "dañado ni protegido con contraseña e inténtalo de nuevo.")


@app.route("/analizar-lote", methods=["POST"])
def analizar_lote():
    """Modo de varios documentos: evalúa cada uno y muestra una tabla."""
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        documentos = [f for f in request.files.getlist("documentos") if f and f.filename]

        # PDF de Word opcionales, emparejados por nombre (para servidores sin Word).
        pdfs_word: dict[str, Path] = {}
        for f in request.files.getlist("pdfs_word"):
            if f and f.filename and f.filename.lower().endswith(".pdf"):
                p = _guardar(f, carpeta / "wpdf")
                if p:
                    pdfs_word[p.stem.lower()] = p

        if not documentos:
            return _error_lote("No subiste ningún documento. Elige uno o varios archivos.")

        resultados, errores = [], []
        for i, archivo in enumerate(documentos):
            work = carpeta / f"item_{i}"
            work.mkdir(parents=True, exist_ok=True)
            doc = _guardar(archivo, work)
            if not doc:
                errores.append({"documento": archivo.filename, "motivo": "archivo vacío"})
                continue
            if _es_pdf(doc) or doc.suffix.lower() not in EXT_DOC:
                errores.append({"documento": doc.name,
                                "motivo": f"formato no admitido ({doc.suffix})"})
                continue
            try:
                emparejado = pdfs_word.get(doc.stem.lower())
                datos = _evaluar_documento(doc, work, pdf_word=emparejado)
                resultados.append(_resumen_doc(datos, doc.name))
            except RuntimeError as exc:
                errores.append({"documento": doc.name, "motivo": _mensaje_error(str(exc))})
            except Exception:                                   # noqa: BLE001
                traceback.print_exc()
                errores.append({"documento": doc.name, "motivo": "error inesperado al procesar"})

        resultados.sort(key=lambda r: r["indice"])              # peor primero
        return render_template("resultado_lote.html", resultados=resultados,
                               errores=errores, caps=CAPS,
                               resumen=_estadisticas_lote(resultados))


def _resumen_doc(datos: dict, nombre: str) -> dict:
    """Resumen compacto de un documento para la tabla de lote."""
    corto = {"fidelidad_visual": "Visual", "conservacion_paginacion": "Paginación",
             "conservacion_fuentes": "Fuentes", "estabilidad_flujo": "Flujo",
             "integridad_objetos": "Objetos"}
    comp = datos["componentes"]
    dims = [{"titulo": t, "corto": corto.get(k, t), "valor": comp[k],
             "peso": int(motor.PESOS[k] * 100)}
            for k, t, _ in DIMENSIONES if k in comp]
    pag = datos["paginas"]
    fuentes = datos.get("fuentes") or {}
    return {
        "documento": nombre,
        "indice": datos["indice"],
        "clasificacion": datos["clasificacion"],
        "problematico": datos["problematico"],
        "modo": datos["modo"],
        "ssim": datos.get("ssim_promedio"),
        "paginas": pag,
        "delta_paginas": pag["objetivo"] - pag["referencia"],
        "dimensiones": dims,
        "sustituciones": (fuentes.get("sustituidas_arbitrarias") or [])
                         + (fuentes.get("sustituidas_seguras") or []),
    }


def _estadisticas_lote(res: list) -> dict:
    if not res:
        return {"n": 0}
    idx = [r["indice"] for r in res]
    return {"n": len(res), "media": round(sum(idx) / len(idx), 1),
            "min": min(idx), "max": max(idx),
            "problematicos": sum(1 for r in res if r["problematico"]),
            "paginacion_rota": sum(1 for r in res if r["delta_paginas"] != 0)}


def _mensaje_error(texto: str) -> str:
    bajo = texto.lower()
    if "bootstrap.ini" in bajo or "no generó" in bajo or "libreoffice no" in bajo:
        return ("LibreOffice no pudo abrir el documento. Puede estar dañado, protegido "
                "o en un formato inesperado.")
    if "password" in bajo or "encrypt" in bajo:
        return "El documento está protegido con contraseña; quítala y reintenta."
    if "pymupdf" in bajo:
        return "Falta la librería de lectura de PDF (pymupdf) en el servidor."
    if texto.startswith("Falta") or texto.startswith("Este servidor"):
        return texto
    return "No se pudo procesar el archivo: " + texto[:160]


def _ok(datos: dict, nombre: str):
    return render_template("resultado.html",
                           r=_construir_resultado(datos, nombre), caps=CAPS)


def _error(mensaje: str, tab: str = "uno"):
    return render_template("index.html", caps=CAPS, error=mensaje, tab=tab,
                           version=motor.VERSION_METRICAS), 400


def _error_lote(mensaje: str):
    return _error(mensaje, tab="varios")


# Alias WSGI para Passenger / gunicorn.
application = app


if __name__ == "__main__":
    print("Capacidades del entorno:", CAPS)
    app.run(host="0.0.0.0", port=5000, debug=False)
