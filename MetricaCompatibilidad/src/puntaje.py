"""
puntaje.py — Índice compuesto provisional de compatibilidad (0-100).

Combina las dimensiones medibles en este Hito en un índice 0-100 (Sección 5).
Para el Hito 1 se usan tres componentes computables de extremo a extremo:

  1. Fidelidad visual         : derivada del SSIM (mapeo de maquetación OOXML->ODF).
  2. Conservación de paginación: penaliza diferencias en el número de páginas.
  3. Conservación de fuentes   : fracción de fuentes de origen presentes en destino,
                                 con crédito PARCIAL cuando hubo una sustitución
                                 segura (métricamente compatible). Que el render se
                                 vea idéntico (SSIM=1.0) no implica que la fuente
                                 pedida exista en destino: la sustitución se registra
                                 porque importa para portabilidad y edición posterior.

Los PESOS son provisionales y uniformes (1/3 cada uno), tal como prescribe el
plan: se inicializan uniformes y se CALIBRAN en la Fase 3 contra el tiempo de
edición observado. Las funciones aceptan parámetros para experimentar.
"""
from __future__ import annotations

PESOS_POR_DEFECTO = {
    "fidelidad_visual": 1 / 3,
    "conservacion_paginacion": 1 / 3,
    "conservacion_fuentes": 1 / 3,
}

# Crédito (0-1) cuando una fuente no está en destino pero sí su sustituta segura.
CREDITO_SUSTITUCION_SEGURA = 0.7


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def componente_visual(ssim_promedio: float) -> float:
    """SSIM (idealmente en [0,1]) -> [0,100]."""
    return round(_clamp(ssim_promedio * 100.0), 1)


def componente_paginacion(paginas_origen: int, paginas_destino: int) -> float:
    """100 si coincide el número de páginas; decae con la diferencia relativa."""
    if paginas_origen <= 0:
        return 0.0
    if paginas_origen == paginas_destino:
        return 100.0
    diff_rel = abs(paginas_origen - paginas_destino) / paginas_origen
    return round(_clamp(100.0 * (1.0 - diff_rel)), 1)


def componente_fuentes(
    fuentes_origen: set[str],
    fuentes_destino: set[str],
    sustituciones: dict | None = None,
    credito_sub: float = CREDITO_SUSTITUCION_SEGURA,
) -> dict:
    """
    Conservación de fuentes con crédito por sustitución segura.

    Para cada fuente de origen:
      - presente exacta en destino           -> 1.0
      - ausente pero su sustituta segura está -> credito_sub (p. ej. 0.7)
      - ausente sin equivalente               -> 0.0

    Devuelve el puntaje [0,100] y el desglose por categoría.
    """
    sustituciones = sustituciones or {}
    if not fuentes_origen:
        return {"puntaje": 100.0, "exactas": [], "sustituidas_seguras": [],
                "perdidas_sin_equivalente": []}

    exactas, sustituidas, perdidas = [], [], []
    acum = 0.0
    for f in sorted(fuentes_origen):
        if f in fuentes_destino:
            exactas.append(f); acum += 1.0
        elif sustituciones.get(f) in fuentes_destino:
            sustituidas.append(f"{f} -> {sustituciones[f]}"); acum += credito_sub
        else:
            perdidas.append(f)
    puntaje = round(_clamp(100.0 * acum / len(fuentes_origen)), 1)
    return {
        "puntaje": puntaje,
        "exactas": exactas,
        "sustituidas_seguras": sustituidas,
        "perdidas_sin_equivalente": perdidas,
    }


def indice_compuesto(componentes: dict, pesos: dict | None = None) -> float:
    """Media ponderada de los componentes -> índice 0-100."""
    pesos = pesos or PESOS_POR_DEFECTO
    total_peso = sum(pesos.get(k, 0.0) for k in componentes)
    if total_peso == 0:
        return 0.0
    acum = sum(componentes[k] * pesos.get(k, 0.0) for k in componentes)
    return round(acum / total_peso, 1)


def calcular(
    ssim_promedio: float,
    paginas_origen: int,
    paginas_destino: int,
    fuentes_origen: set[str],
    fuentes_destino: set[str],
    sustituciones: dict | None = None,
    pesos: dict | None = None,
) -> dict:
    """Calcula los componentes y el índice compuesto; devuelve el desglose."""
    fuentes_info = componente_fuentes(fuentes_origen, fuentes_destino, sustituciones)
    comp = {
        "fidelidad_visual": componente_visual(ssim_promedio),
        "conservacion_paginacion": componente_paginacion(paginas_origen, paginas_destino),
        "conservacion_fuentes": fuentes_info["puntaje"],
    }
    indice = indice_compuesto(comp, pesos)
    return {
        "componentes": comp,
        "detalle_fuentes": {k: v for k, v in fuentes_info.items() if k != "puntaje"},
        "pesos": pesos or PESOS_POR_DEFECTO,
        "indice_compatibilidad": indice,
    }
