"""
conversion.py — Conversión de documentos con LibreOffice en modo headless.

Implementa el paso (b) del pipeline (Sección 5 del plan): convertir el documento
de origen a otro formato (OOXML -> ODF) y renderizar a PDF para la comparación
visual posterior. Usa un perfil de usuario aislado por llamada para evitar
bloqueos de LibreOffice y permitir ejecución en lote reproducible (incluso en
contenedores/CI).

Probado con LibreOffice 24.2 (ver requirements.txt / protocolo experimental).
"""
from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

# Nombres posibles del binario de LibreOffice según el sistema operativo.
_BINARIOS_CANDIDATOS = ["soffice", "libreoffice", "soffice.bin"]


def localizar_soffice() -> str:
    """Devuelve la ruta al binario de LibreOffice o lanza RuntimeError."""
    for nombre in _BINARIOS_CANDIDATOS:
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    # Rutas habituales en macOS / Windows como último recurso.
    candidatos_fijos = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
    ]
    for ruta in candidatos_fijos:
        if Path(ruta).exists():
            return ruta
    raise RuntimeError(
        "No se encontró LibreOffice (soffice). Instálalo o añádelo al PATH."
    )


def convertir(
    origen: str | Path,
    formato: str,
    salida_dir: str | Path,
    timeout: int = 180,
) -> Path:
    """
    Convierte `origen` al `formato` indicado y deja el resultado en `salida_dir`.

    Parámetros
    ----------
    origen : ruta al archivo de entrada (.docx, .odt, ...).
    formato : extensión destino para `--convert-to` (p. ej. 'odt', 'pdf').
    salida_dir : carpeta donde LibreOffice escribirá el archivo convertido.
    timeout : segundos máximos antes de abortar la conversión.

    Devuelve
    --------
    Path al archivo convertido.
    """
    origen = Path(origen).resolve()
    salida_dir = Path(salida_dir).resolve()
    salida_dir.mkdir(parents=True, exist_ok=True)

    if not origen.exists():
        raise FileNotFoundError(f"No existe el archivo de origen: {origen}")

    soffice = localizar_soffice()
    # Perfil de usuario único => evita el bloqueo "soffice ya está en ejecución"
    # y hace la conversión segura para lotes y entornos aislados.
    perfil = f"/tmp/lo_perfil_{uuid.uuid4().hex}"

    cmd = [
        soffice,
        "--headless",
        "--convert-to",
        formato,
        "--outdir",
        str(salida_dir),
        f"-env:UserInstallation=file://{perfil}",
        str(origen),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Falló la conversión de {origen.name} a {formato}.\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )

    destino = salida_dir / (origen.stem + "." + formato)
    if not destino.exists():
        raise RuntimeError(
            f"LibreOffice no produjo el archivo esperado: {destino}\n"
            f"Salida: {proc.stdout}"
        )
    return destino
