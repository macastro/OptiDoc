"""
Prueba de sensibilidad del índice compuesto: verifica que el puntaje RESPONDE
a la degradación de cada dimensión (no es constante). Ejecutar:
    python tests/test_puntaje.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import puntaje  # noqa: E402

SUST = {"Arial": "Liberation Sans"}


def caso(nombre, **kw):
    r = puntaje.calcular(**kw)
    print(f"  {nombre:32} -> indice {r['indice_compatibilidad']:>6}  {r['componentes']}")
    return r["indice_compatibilidad"]


def main():
    print("Sensibilidad del índice compuesto (0-100):")
    base = dict(ssim_promedio=1.0, paginas_origen=4, paginas_destino=4,
                fuentes_origen={"Calibri"}, fuentes_destino={"Calibri"}, sustituciones=SUST)
    perfecto = caso("conversión perfecta", **base)

    peor_visual = caso("SSIM bajo (0.80)", **{**base, "ssim_promedio": 0.80})
    peor_pag = caso("cambia paginación (4->5)", **{**base, "paginas_destino": 5})
    sub_seg = caso("sustitución segura (Arial)",
                   **{**base, "fuentes_origen": {"Arial"}, "fuentes_destino": {"Liberation Sans"}})
    fuente_perdida = caso("fuente perdida sin equiv.",
                          **{**base, "fuentes_origen": {"Brush Script"}, "fuentes_destino": {"Calibri"}})

    assert perfecto == 100.0
    assert peor_visual < perfecto, "el índice debe bajar si baja el SSIM"
    assert peor_pag < perfecto, "el índice debe bajar si cambia la paginación"
    assert sub_seg < perfecto, "una sustitución segura debe penalizar parcialmente"
    assert fuente_perdida < sub_seg, "perder una fuente debe penalizar más que sustituirla"
    print("\nOK: el índice responde correctamente a cada degradación.")


if __name__ == "__main__":
    main()
