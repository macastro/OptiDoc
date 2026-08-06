"""
motor.py — Motor de cálculo portable de la métrica de compatibilidad.

Diseñado para funcionar en tres entornos con el MISMO código:

  * Local / VPS (con LibreOffice): acepta un .docx, lo renderiza y compara.
  * Hosting compartido (sin LibreOffice): acepta dos PDF ya generados
    (el de Word y el de LibreOffice) y los compara.

Para lograrlo, el procesamiento de PDF usa PyMuPDF (rasterizado, fuentes, texto,
objetos) en lugar de Poppler, y el SSIM se implementa con NumPy. Así las únicas
dependencias del cálculo son: pymupdf, numpy, pillow. LibreOffice solo se usa
—cuando está disponible— para convertir un .docx a PDF.

Las métricas, pesos y umbrales replican el conjunto CONGELADO del Hito 2
(src/metricas_prioritarias.py). Si aquellos cambian, actualizar también aquí.
"""
from __future__ import annotations

import platform
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import numpy as np

try:
    import fitz  # PyMuPDF
    _TIENE_FITZ = True
except ImportError:
    _TIENE_FITZ = False


# ===========================================================================
# CONJUNTO CONGELADO (debe coincidir con src/metricas_prioritarias.py)
# ===========================================================================
VERSION_METRICAS = "2.0-hito2-congelado"

PESOS = {
    "fidelidad_visual": 0.30,
    "conservacion_paginacion": 0.25,
    "conservacion_fuentes": 0.20,
    "estabilidad_flujo": 0.15,
    "integridad_objetos": 0.10,
}
UMBRAL_PROBLEMATICO = 90.0

# Sustituciones tipográficas métricamente compatibles (crédito parcial).
SUSTITUCIONES_SEGURAS = {
    "arial": "liberation sans", "helvetica": "liberation sans",
    "times new roman": "liberation serif", "times": "liberation serif",
    "courier new": "liberation mono", "courier": "liberation mono",
    "calibri": "carlito", "cambria": "caladea",
}


# ===========================================================================
# Detección de capacidades del entorno
# ===========================================================================
def localizar_soffice() -> str | None:
    """Devuelve la ruta a LibreOffice (soffice) o None si no está instalado."""
    for nombre in ("soffice", "libreoffice"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    for ruta in ("/usr/bin/soffice", "/opt/libreoffice/program/soffice",
                 "/Applications/LibreOffice.app/Contents/MacOS/soffice",
                 # En Windows se prefiere soffice.com (consola que espera a que
                 # termine y devuelve la salida); soffice.exe puede desconectarse
                 # antes de escribir el PDF.
                 r"C:\Program Files\LibreOffice\program\soffice.com",
                 r"C:\Program Files\LibreOffice\program\soffice.exe",
                 r"C:\Program Files (x86)\LibreOffice\program\soffice.com",
                 r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if Path(ruta).exists():
            return ruta
    return None


def tiene_word() -> bool:
    """True si Microsoft Word está instalado y automatizable (solo Windows)."""
    if platform.system() != "Windows":
        return False
    try:
        import winreg
    except ImportError:
        return False
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application"))
        return True
    except OSError:
        return False


def capacidades() -> dict:
    """Informa qué puede hacer este entorno."""
    tiene_lo = localizar_soffice() is not None
    tiene_wd = tiene_word()
    return {
        "pymupdf": _TIENE_FITZ,
        "libreoffice": tiene_lo,
        "word": tiene_wd,
        # Con Word o LibreOffice se acepta un .docx; sin ninguno, solo dos PDF.
        "acepta_docx": (tiene_lo or tiene_wd) and _TIENE_FITZ,
        # Caso ideal (Windows con ambos): el usuario sube UN solo archivo y el
        # servidor genera la referencia con Word y el objetivo con LibreOffice.
        "solo_documento": tiene_wd and tiene_lo and _TIENE_FITZ,
        "acepta_pdf": _TIENE_FITZ,
    }


# ===========================================================================
# Conversión con LibreOffice (solo cuando está disponible)
# ===========================================================================
def convertir(documento: Path, formato: str, salida_dir: Path, timeout: int = 180) -> Path:
    """Convierte un documento al formato dado con LibreOffice headless."""
    soffice = localizar_soffice()
    if not soffice:
        raise RuntimeError("LibreOffice no está disponible en este entorno.")
    documento, salida_dir = Path(documento), Path(salida_dir)
    salida_dir.mkdir(parents=True, exist_ok=True)
    # Perfil de usuario aislado (permite convertir aunque LibreOffice esté abierto).
    # Se pasa como URL de archivo VÁLIDA en cada sistema: Path.as_uri() genera
    # file:///C:/... en Windows y file:///tmp/... en Linux. Construir la URL a mano
    # rompía el arranque en Windows -> error "bootstrap.ini está dañado".
    perfil_dir = Path(tempfile.gettempdir()) / f"lo_perfil_{uuid.uuid4().hex}"
    cmd = [soffice, "--headless", f"-env:UserInstallation={perfil_dir.as_uri()}",
           "--convert-to", formato, "--outdir", str(salida_dir), str(documento)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    destino = salida_dir / (documento.stem + "." + formato.split(":")[0])
    if not destino.exists():
        detalle = (proc.stderr or proc.stdout or "").strip()[:300]
        raise RuntimeError(f"LibreOffice no generó '{formato}'. {detalle}")
    return destino


def convertir_a_pdf(documento: Path, salida_dir: Path, timeout: int = 180) -> Path:
    """Convierte un documento a PDF con LibreOffice headless."""
    return convertir(documento, "pdf", salida_dir, timeout)


def convertir_con_word(documento: Path, salida_dir: Path) -> Path:
    """Convierte un documento a PDF usando Microsoft Word (automatización COM).

    Solo funciona en Windows con Word instalado. Es la referencia "real" de cómo
    se ve el documento en Word, sin depender de que el usuario exporte el PDF a
    mano. Pensado para uso local de un solo usuario (Word no es concurrente).
    """
    if platform.system() != "Windows":
        raise RuntimeError("La conversión con Word solo está disponible en Windows.")
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "Falta pywin32 para automatizar Word. Instálalo con: pip install pywin32"
        ) from exc

    documento = Path(documento).resolve()
    salida_dir = Path(salida_dir)
    salida_dir.mkdir(parents=True, exist_ok=True)
    destino = (salida_dir / (documento.stem + ".pdf")).resolve()

    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        try:
            word.DisplayAlerts = False
        except Exception:                                       # noqa: BLE001
            pass
        doc = word.Documents.Open(str(documento), ReadOnly=True)
        try:
            doc.ExportAsFixedFormat(str(destino), 17)           # 17 = wdExportFormatPDF
        finally:
            doc.Close(False)
        if not destino.exists():
            raise RuntimeError("Word no generó el PDF.")
        return destino
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:                                   # noqa: BLE001
                pass
        pythoncom.CoUninitialize()


# ===========================================================================
# Lectura de PDF con PyMuPDF (portable, sin Poppler)
# ===========================================================================
def _abrir(pdf: Path):
    if not _TIENE_FITZ:
        raise RuntimeError("PyMuPDF (pymupdf) es necesario para leer PDF.")
    return fitz.open(str(pdf))


def n_paginas(pdf: Path) -> int:
    doc = _abrir(pdf)
    try:
        return doc.page_count
    finally:
        doc.close()


def rasterizar(pdf: Path, dpi: int = 150) -> list[np.ndarray]:
    """Rasteriza cada página a escala de grises en [0, 1]."""
    doc = _abrir(pdf)
    paginas, zoom = [], dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    try:
        for page in doc:
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, alpha=False)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
            paginas.append(arr.astype(np.float64) / 255.0)
    finally:
        doc.close()
    return paginas


def fuentes_pdf(pdf: Path) -> set[str]:
    """Fuentes usadas en el PDF (sin el prefijo de subconjunto)."""
    doc = _abrir(pdf)
    fuentes: set[str] = set()
    try:
        for page in doc:
            for f in page.get_fonts(full=True):
                nombre = f[3] if len(f) > 3 else ""
                nombre = re.sub(r"^[A-Z]{6}\+", "", str(nombre))
                if nombre:
                    fuentes.add(nombre)
    finally:
        doc.close()
    return fuentes


def texto_lineas(pdf: Path, pagina: int) -> list[str]:
    """Líneas de texto de una página (1-based), con espacios normalizados."""
    doc = _abrir(pdf)
    try:
        if pagina - 1 >= doc.page_count:
            return []
        txt = doc[pagina - 1].get_text("text")
    finally:
        doc.close()
    salida = []
    for l in txt.splitlines():
        l = re.sub(r"\s+", " ", l).strip()
        if l:
            salida.append(l)
    return salida


def contar_imagenes(pdf: Path) -> int:
    doc = _abrir(pdf)
    try:
        return sum(len(page.get_images(full=True)) for page in doc)
    finally:
        doc.close()


# ===========================================================================
# SSIM en NumPy (ventana uniforme 7×7, equivalente a scikit-image por defecto)
# ===========================================================================
def _media_ventana(img: np.ndarray, w: int) -> np.ndarray:
    """Media sobre ventanas w×w válidas, vía imagen integral (O(n))."""
    S = np.cumsum(np.cumsum(img, axis=0), axis=1)
    S = np.pad(S, ((1, 0), (1, 0)), mode="constant")
    total = S[w:, w:] - S[:-w, w:] - S[w:, :-w] + S[:-w, :-w]
    return total / (w * w)


def ssim(a: np.ndarray, b: np.ndarray, w: int = 7) -> float:
    """SSIM global entre dos imágenes en [0, 1]. Redimensiona b si difiere."""
    if a.shape != b.shape:
        from PIL import Image
        im = Image.fromarray((b * 255).astype(np.uint8)).resize(
            (a.shape[1], a.shape[0]), Image.LANCZOS)
        b = np.asarray(im, dtype=np.float64) / 255.0
    if min(a.shape) < w:
        w = max(3, min(a.shape) // 2 * 2 + 1)
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    NP = w * w
    cov_norm = NP / (NP - 1)                       # corrección muestral (como skimage)

    mu_a = _media_ventana(a, w)
    mu_b = _media_ventana(b, w)
    mu_aa = _media_ventana(a * a, w)
    mu_bb = _media_ventana(b * b, w)
    mu_ab = _media_ventana(a * b, w)

    var_a = cov_norm * (mu_aa - mu_a ** 2)
    var_b = cov_norm * (mu_bb - mu_b ** 2)
    cov_ab = cov_norm * (mu_ab - mu_a * mu_b)

    num = (2 * mu_a * mu_b + C1) * (2 * cov_ab + C2)
    den = (mu_a ** 2 + mu_b ** 2 + C1) * (var_a + var_b + C2)
    mapa = num / den
    return float(np.clip(mapa.mean(), -1.0, 1.0))


def indices_representativos(n: int) -> list[int]:
    """Primera, intermedia y última página (0-based)."""
    if n <= 0:
        return []
    if n <= 3:
        return list(range(n))
    return sorted({0, n // 2, n - 1})


# ===========================================================================
# Las cinco métricas prioritarias (cross-engine: referencia Word vs objetivo LO)
# ===========================================================================
def _familia(f: str) -> str:
    base = re.split(r"[-,]", f)[0]
    base = re.sub(r"(MT|PS|Std|Pro)$", "", base)
    return base.strip().lower()


def metricas_cross(pdf_referencia: Path, pdf_objetivo: Path, dpi: int = 150) -> dict:
    """Calcula las cinco métricas entre el PDF de Word y el de LibreOffice."""
    pag_ref = rasterizar(pdf_referencia, dpi)
    pag_obj = rasterizar(pdf_objetivo, dpi)
    n_ref, n_obj = len(pag_ref), len(pag_obj)

    # 1) Fidelidad visual (SSIM en páginas representativas)
    indices = indices_representativos(max(n_ref, n_obj))
    ssims, detalle_vis = [], []
    for i in indices:
        if i < n_ref and i < n_obj:
            v = ssim(pag_ref[i], pag_obj[i])
            ssims.append(v)
            detalle_vis.append({"pagina": i + 1, "ssim": round(v, 4)})
    ssim_prom = float(np.mean(ssims)) if ssims else 0.0
    vis = round(ssim_prom * 100, 1)

    # 2) Conservación de paginación
    if n_ref == 0:
        pag = 0.0
    elif n_ref == n_obj:
        pag = 100.0
    else:
        pag = round(max(0.0, 100.0 * (1 - abs(n_ref - n_obj) / n_ref)), 1)

    # 3) Conservación de fuentes
    f_ref, f_obj = fuentes_pdf(pdf_referencia), fuentes_pdf(pdf_objetivo)
    fam_obj = {_familia(x) for x in f_obj}
    seg = {_familia(k): _familia(v) for k, v in SUSTITUCIONES_SEGURAS.items()}
    conserv, sustseg, sustarb = [], [], []
    for f in sorted({_familia(x) for x in f_ref}):
        if f in fam_obj:
            conserv.append(f)
        elif seg.get(f) in fam_obj:
            sustseg.append(f"{f} → {seg[f]}")
        else:
            sustarb.append(f)
    tot = len(conserv) + len(sustseg) + len(sustarb)
    fue = 100.0 if tot == 0 else round(100.0 * (len(conserv) + 0.6 * len(sustseg)) / tot, 1)

    # 4) Estabilidad del flujo (reflujo de líneas)
    import difflib
    pags_txt = [i + 1 for i in indices if i < min(n_ref, n_obj)] or [1]
    sims = []
    for p in pags_txt:
        lr, lo = texto_lineas(pdf_referencia, p), texto_lineas(pdf_objetivo, p)
        if lr and lo:
            sims.append(difflib.SequenceMatcher(None, lr, lo).ratio())
        elif not lr and not lo:
            continue
        else:
            sims.append(0.0)
    flu = round(float(np.mean(sims)) * 100, 1) if sims else 100.0

    # 5) Integridad de objetos
    o_ref, o_obj = contar_imagenes(pdf_referencia), contar_imagenes(pdf_objetivo)
    obj = 100.0 if o_ref == 0 else round(100.0 * min(o_obj, o_ref) / o_ref, 1)

    componentes = {
        "fidelidad_visual": vis, "conservacion_paginacion": pag,
        "conservacion_fuentes": fue, "estabilidad_flujo": flu,
        "integridad_objetos": obj,
    }
    indice = indice_compuesto(componentes)
    return {
        "modo": "cross-engine",
        "componentes": componentes,
        "indice": indice,
        "clasificacion": clasificar(indice),
        "problematico": indice < UMBRAL_PROBLEMATICO,
        "paginas": {"referencia": n_ref, "objetivo": n_obj},
        "ssim_promedio": round(ssim_prom, 4),
        "detalle_visual": detalle_vis,
        "fuentes": {"referencia": sorted(f_ref), "objetivo": sorted(f_obj),
                    "conservadas": conserv, "sustituidas_seguras": sustseg,
                    "sustituidas_arbitrarias": sustarb},
        "objetos": {"referencia": o_ref, "objetivo": o_obj},
        "figura_paginas": (pag_ref, pag_obj, indices),
    }


def metricas_mapeo(pdf_origen: Path, pdf_odt: Path, dpi: int = 150) -> dict:
    """Comparación de mapeo (sin Word): render del original vs render del ODT.

    Solo dispone de fidelidad visual y conservación de paginación, porque sin un
    PDF de Word no hay referencia de fuentes/flujo de la suite de origen. Se
    reporta como diagnóstico del mapeo a ODF, no como métrica cross-engine.
    """
    pag_a = rasterizar(pdf_origen, dpi)
    pag_b = rasterizar(pdf_odt, dpi)
    n_a, n_b = len(pag_a), len(pag_b)
    indices = indices_representativos(max(n_a, n_b))
    ssims, detalle = [], []
    for i in indices:
        if i < n_a and i < n_b:
            v = ssim(pag_a[i], pag_b[i])
            ssims.append(v)
            detalle.append({"pagina": i + 1, "ssim": round(v, 4)})
    ssim_prom = float(np.mean(ssims)) if ssims else 0.0
    vis = round(ssim_prom * 100, 1)
    pag = 100.0 if (n_a and n_a == n_b) else (
        round(max(0.0, 100.0 * (1 - abs(n_a - n_b) / n_a)), 1) if n_a else 0.0)
    componentes = {"fidelidad_visual": vis, "conservacion_paginacion": pag}
    indice = indice_compuesto(componentes)
    return {
        "modo": "mapeo-odf",
        "componentes": componentes,
        "indice": indice,
        "clasificacion": clasificar(indice),
        "problematico": indice < UMBRAL_PROBLEMATICO,
        "paginas": {"referencia": n_a, "objetivo": n_b},
        "ssim_promedio": round(ssim_prom, 4),
        "detalle_visual": detalle,
        "figura_paginas": (pag_a, pag_b, indices),
    }


# ===========================================================================
# Índice compuesto y clasificación (pesos congelados)
# ===========================================================================
def indice_compuesto(componentes: dict) -> float:
    total = sum(PESOS[k] for k in componentes if k in PESOS)
    if total == 0:
        return 0.0
    acum = sum(componentes[k] * PESOS[k] for k in componentes if k in PESOS)
    return round(acum / total, 2)


def clasificar(indice: float) -> str:
    if indice >= 95:
        return "alta"
    if indice >= UMBRAL_PROBLEMATICO:
        return "aceptable"
    if indice >= 70:
        return "baja"
    return "critica"


# ===========================================================================
# Figura de diferencias (PNG en memoria) — opcional, requiere matplotlib
# ===========================================================================
def figura_diferencias(pag_ref: list, pag_obj: list, indices: list,
                       etiqueta_a="Word", etiqueta_b="LibreOffice") -> bytes | None:
    """Devuelve un PNG (bytes) con origen | destino | diferencia, o None."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    evaluadas = [(i, pag_ref[i], pag_obj[i]) for i in indices
                 if i < len(pag_ref) and i < len(pag_obj)]
    if not evaluadas:
        return None
    # Página con mayor diferencia
    def dif(par):
        a, b = par[1], par[2]
        if a.shape != b.shape:
            from PIL import Image
            b = np.asarray(Image.fromarray((b * 255).astype(np.uint8)).resize(
                (a.shape[1], a.shape[0]))) / 255.0
        return np.abs(a - b).mean()
    i, a, b = max(evaluadas, key=dif)
    if a.shape != b.shape:
        from PIL import Image
        b = np.asarray(Image.fromarray((b * 255).astype(np.uint8)).resize(
            (a.shape[1], a.shape[0]))) / 255.0
    d = np.abs(a - b)
    import io
    fig, ax = plt.subplots(1, 3, figsize=(13, 6))
    ax[0].imshow(a, cmap="gray"); ax[0].set_title(f"{etiqueta_a} · pág {i+1}")
    ax[1].imshow(b, cmap="gray"); ax[1].set_title(f"{etiqueta_b} · pág {i+1}")
    im = ax[2].imshow(d, cmap="inferno", vmin=0, vmax=max(d.max(), 1e-6))
    ax[2].set_title(f"|Diferencia| · SSIM={ssim(a, b):.4f}")
    for e in ax:
        e.axis("off")
    fig.colorbar(im, ax=ax[2], fraction=0.046)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
