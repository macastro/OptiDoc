"""
passenger_wsgi.py — Punto de entrada para hosting con Passenger (cPanel).

Lo usan los paneles que ofrecen "Setup Python App" (cPanel). Passenger busca una
variable llamada `application`; aquí la tomamos de app.py.

NOTA: el plan compartido de Hostinger NO ejecuta Python (usa hPanel, sin gestor
de apps Python). Este archivo sirve en hosts basados en cPanel que sí ofrecen
"Setup Python App", o en un VPS. Ver README_DESPLIEGUE.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import app as application  # noqa: E402  (Passenger requiere 'application')
