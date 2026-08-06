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
    return render_template("index.html", caps=CAPS, version=motor.VERSION_METRICAS)


@app.route("/analizar", methods=["POST"])
def analizar():
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

            # --- Ruta B: documento de Word ---
            if doc:
                if _es_pdf(doc):
                    return _error("Subiste un PDF en la casilla del documento. "
                                  "Usa las casillas de PDF, o sube el .docx aquí.")
                if doc.suffix.lower() not in EXT_DOC:
                    return _error(f"Formato no admitido: {doc.suffix}. "
                                  "Usa .docx, .doc, .odt o .rtf.")

                # Objetivo = cómo abre LibreOffice el documento.
                obj_pdf = None
                if CAPS["libreoffice"]:
                    obj_pdf = motor.convertir(doc, "pdf", carpeta / "obj")
                elif pdf_lo and _es_pdf(pdf_lo):
                    obj_pdf = pdf_lo

                # Referencia = cómo se ve en Word. Si hay Word, se genera solo.
                ref_pdf = None
                if CAPS["word"]:
                    ref_pdf = motor.convertir_con_word(doc, carpeta / "ref")
                elif pdf_word and _es_pdf(pdf_word):
                    ref_pdf = pdf_word

                # Caso ideal: tenemos ambas versiones -> métrica cross-engine real.
                if ref_pdf and obj_pdf:
                    datos = motor.metricas_cross(ref_pdf, obj_pdf)
                    return _ok(datos, doc.name)

                # Hay objetivo (LibreOffice) pero no referencia (no Word ni su PDF).
                if obj_pdf and not ref_pdf:
                    if CAPS["libreoffice"]:
                        odt = motor.convertir(doc, "odt", carpeta / "odt")
                        odt_pdf = motor.convertir(odt, "pdf", carpeta / "odtpdf")
                        datos = motor.metricas_mapeo(obj_pdf, odt_pdf)
                        return _ok(datos, doc.name)
                    return _error("Falta la referencia de Word. Sube también el PDF "
                                  "exportado desde Word.")

                # Hay referencia (Word) pero no objetivo (sin LibreOffice ni su PDF).
                if ref_pdf and not obj_pdf:
                    return _error("Este equipo generó la versión de Word, pero falta la de "
                                  "LibreOffice. Instala LibreOffice o sube el PDF exportado "
                                  "desde LibreOffice.")

                return _error("Este servidor no puede convertir el documento. Sube el PDF "
                              "de Word y el PDF de LibreOffice ya generados.")

            return _error("No subiste ningún archivo. Elige un documento (o dos PDF).")

        except RuntimeError as exc:
            return _error(_mensaje_error(str(exc)))
        except Exception:                                       # noqa: BLE001
            traceback.print_exc()
            return _error("Ocurrió un error al procesar el archivo. Verifica que no esté "
                          "dañado ni protegido con contraseña e inténtalo de nuevo.")


def _mensaje_error(texto: str) -> str:
    bajo = texto.lower()
    if "libreoffice no generó" in bajo or "convert" in bajo:
        return ("LibreOffice no pudo abrir el documento. Puede estar dañado, protegido "
                "o en un formato inesperado.")
    if "password" in bajo or "encrypt" in bajo:
        return "El documento está protegido con contraseña; quita la protección y reintenta."
    if "pymupdf" in bajo:
        return "Falta la librería de lectura de PDF (pymupdf) en el servidor."
    return "No se pudo procesar el archivo: " + texto[:160]


def _ok(datos: dict, nombre: str):
    return render_template("resultado.html",
                           r=_construir_resultado(datos, nombre), caps=CAPS)


def _error(mensaje: str):
    return render_template("index.html", caps=CAPS, error=mensaje,
                           version=motor.VERSION_METRICAS), 400


# Alias WSGI para Passenger / gunicorn.
application = app


if __name__ == "__main__":
    print("Capacidades del entorno:", CAPS)
    app.run(host="0.0.0.0", port=5000, debug=False)
