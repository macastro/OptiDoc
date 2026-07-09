"""
Calcula un índice de compatibilidad entre 0 y 100 combinando tres aspectos:

  1. Fidelidad visual:       qué tan parecida se ve la página tras la conversión (SSIM).
  2. Conservación de páginas: si el número de páginas cambió.
  3. Conservación de fuentes: qué fracción de las fuentes del original llegaron al destino.
                              Las sustituciones "seguras" (mismas métricas de letra) cuentan
                              con crédito parcial — aunque el render se vea igual, la fuente
                              pedida no existe en destino y eso importa si alguien edita después.

Los tres pesos son iguales por ahora (1/3 cada uno) y pueden ajustarse cuando
haya datos reales de cuánto trabajo genera cada tipo de diferencia.
"""
from __future__ import annotations

PESOS_POR_DEFECTO = {
    "fidelidad_visual": 1 / 3,
    "conservacion_paginacion": 1 / 3,
    "conservacion_fuentes": 1 / 3,
}

# Puntuación parcial cuando la fuente exacta no llegó pero sí un equivalente seguro.
CREDITO_SUSTITUCION_SEGURA = 0.7


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def componente_visual(ssim_promedio: float) -> float:
    """Convierte el valor SSIM (0-1) a una escala de 0 a 100."""
    return round(_clamp(ssim_promedio * 100.0), 1)


def componente_paginacion(paginas_origen: int, paginas_destino: int) -> float:
    """Da 100 si el número de páginas es igual; baja proporcionalmente si hay diferencia."""
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
    Calcula qué porcentaje de las fuentes del original llegaron al documento convertido.

    Para cada fuente:
      - Si está tal cual en el destino: puntuación completa.
      - Si no está pero sí un equivalente seguro: puntuación parcial (credito_sub).
      - Si no hay nada parecido: cero.

    Devuelve la puntuación y un desglose de qué pasó con cada fuente.
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
    """Combina los componentes en un solo número de 0 a 100 usando la media ponderada."""
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
    """Calcula todos los componentes y los combina en el índice final con su desglose."""
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
