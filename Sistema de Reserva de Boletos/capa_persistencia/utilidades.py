"""Conversión entre los formatos del contrato (mensajes.py) y los tipos de Python."""
from datetime import datetime

from comun.mensajes import meses

FORMATO_FECHA = "%Y/%m/%d"    # el formato con barras que envía el cliente: "2026/11/07"


def numero_mes(nombre):
    """'noviembre' -> 11. Lanza ValueError si el mes no existe."""
    return meses.index(str(nombre).strip().lower()) + 1


def leer_fecha(texto):
    """'2026/11/07' -> date(2026, 11, 7). Lanza ValueError si el formato no coincide."""
    return datetime.strptime(str(texto), FORMATO_FECHA).date()


def escribir_fecha(fecha):
    """date(2026, 11, 7) -> '2026/11/07', para responder en el mismo formato."""
    return fecha.strftime(FORMATO_FECHA)
