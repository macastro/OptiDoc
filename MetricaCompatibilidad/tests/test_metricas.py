"""
Prueba de la métrica visual SSIM sobre arreglos sintéticos (sin archivos).
Ejecutar:  python tests/test_metricas.py
"""
import sys
from pathlib import Path

import numpy as np
from skimage.metrics import structural_similarity as ssim

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    rng = np.random.default_rng(0)
    img = rng.random((256, 256))
    identica = ssim(img, img, data_range=1.0)
    desplazada = ssim(img, np.roll(img, 8, axis=0), data_range=1.0)
    print(f"SSIM(idéntica)   = {identica:.4f}")
    print(f"SSIM(desplazada) = {desplazada:.4f}")
    assert identica > 0.999, "SSIM de una imagen consigo misma debe ser ~1"
    assert desplazada < identica, "SSIM debe bajar ante un desplazamiento"
    print("OK: la métrica SSIM está bien implementada y es sensible.")


if __name__ == "__main__":
    main()
