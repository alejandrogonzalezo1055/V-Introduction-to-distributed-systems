"""Conexión y preparación explícita de PostgreSQL; no borra datos existentes."""

import argparse
import calendar
from datetime import date
import json
import os
from pathlib import Path
import re

import psycopg
from psycopg.rows import dict_row


def conectar(url=None):
    """Usa SRB_DATABASE_URL o las variables estándar PGHOST, PGUSER, etc."""
    conexion = psycopg.connect(
        url if url is not None else os.environ.get("SRB_DATABASE_URL", ""),
        autocommit=True, row_factory=dict_row, connect_timeout=5,
    )
    conexion.execute("SET statement_timeout = '5s'")
    conexion.execute("SET lock_timeout = '3s'")
    return conexion


def limites_mes(mes):
    if not isinstance(mes, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", mes):
        raise ValueError("Use mes con formato YYYY-MM, por ejemplo 2026-10.")
    anio, numero = map(int, mes.split("-"))
    inicio = date(anio, numero, 1)
    # PostgreSQL admite años mayores; el contrato usa fechas de Python.
    fin = date(anio + 1, 1, 1) if numero == 12 else date(anio, numero + 1, 1)
    return inicio, fin


def crear_esquema(conexion):
    sql = Path(__file__).with_name("esquema.sql").read_text(encoding="utf-8")
    with conexion.transaction():
        conexion.execute(sql)


def cargar_datos(conexion, mes="2026-10", eventos=50, dobles=20, capacidad=100):
    inicio, _ = limites_mes(mes)
    if not 1 <= eventos <= 10000 or not 0 <= dobles <= eventos or not 1 <= capacidad <= 2147483647:
        raise ValueError("Revise eventos (1-10000), dobles (0-eventos) y capacidad positiva.")
    dias = calendar.monthrange(inicio.year, inicio.month)[1]
    with conexion.transaction():
        # La carga inicial es administrativa y se realiza antes de atender clientes.
        conexion.execute("LOCK TABLE eventos, ocurrencias, reservas IN EXCLUSIVE MODE")
        if conexion.execute("SELECT 1 FROM eventos LIMIT 1").fetchone():
            raise ValueError("Ya existen eventos: no se sobrescriben los datos.")
        for indice in range(1, eventos + 1):
            evento = f"E{indice}"
            conexion.execute("INSERT INTO eventos VALUES (%s, %s, %s)",
                             (evento, f"Evento universitario {indice}", "cultural"))
            dia = 1 + (indice - 1) % (dias - 1)
            for numero in range(1, (2 if indice <= dobles else 1) + 1):
                conexion.execute("""
                    INSERT INTO ocurrencias (id_evento, numero, fecha, capacidad)
                    VALUES (%s, %s, %s, %s)
                """, (evento, numero, date(inicio.year, inicio.month, dia + numero - 1), capacidad))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accion", choices=["iniciar", "estado"])
    parser.add_argument("--mes", default="2026-10")
    parser.add_argument("--eventos", type=int, default=50)
    parser.add_argument("--dobles", type=int, default=20)
    parser.add_argument("--capacidad", type=int, default=100)
    args = parser.parse_args()
    try:
        with conectar() as conexion:
            if args.accion == "iniciar":
                crear_esquema(conexion)
                cargar_datos(conexion, args.mes, args.eventos, args.dobles, args.capacidad)
                print(f"Creados {args.eventos} eventos y {args.eventos + args.dobles} ocurrencias.")
            else:
                # Tablas fijas, no nombres recibidos de una petición de red.
                datos = {tabla: conexion.execute(f"SELECT * FROM {tabla} ORDER BY 1, 2").fetchall()
                         for tabla in ("eventos", "ocurrencias", "reservas")}
                print(json.dumps(datos, default=str, ensure_ascii=False, indent=2))
    except ValueError as exc:
        parser.error(str(exc))
    except psycopg.Error:
        parser.exit(1, "No se pudo preparar o leer PostgreSQL. Revise conexión, permisos y esquema.\n")


if __name__ == "__main__":
    main()
