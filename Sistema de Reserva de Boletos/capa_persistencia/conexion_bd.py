"""Conexión a la base de datos: un engine y una fábrica de sesiones por proceso."""
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from comun.config import DB_URL

if not DB_URL or DB_URL == "*":
    raise RuntimeError(
        "Falta DB_URL en el .env. Ejemplo: "
        "DB_URL=postgresql+psycopg://srb:srb@localhost:5432/srb"
    )

engine = create_engine(DB_URL)          # contiene el pool de conexiones
SessionLocal = sessionmaker(engine)     # una Session por petición


def esperar_bd(intentos=15, pausa=2.0):
    """Espera a que la base acepte conexiones (el contenedor tarda unos segundos)."""
    for i in range(1, intentos + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[BD] conectada")
            return
        except Exception as error:
            print(f"[BD] no disponible (intento {i}/{intentos}): {error.__class__.__name__}")
            time.sleep(pausa)
    raise RuntimeError("La base de datos no respondió. ¿Está corriendo el contenedor?")
