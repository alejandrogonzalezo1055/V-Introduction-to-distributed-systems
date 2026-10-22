"""Solo almacenamiento importa este módulo y conoce las credenciales de PostgreSQL.

engine representa la conexión configurable a la BD; SessionLocal crea sesiones
breves para cada operación. Crear el engine no abre aún una conexión de red.
"""
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from comun.config import DB_URL

if not DB_URL or DB_URL == "*":
    raise RuntimeError(
        "Falta DB_URL en el .env. Ejemplo: "
        "DB_URL=postgresql+psycopg://srb:srb@localhost:5432/srb"
    )

# connect_timeout limita una conexión TCP equivocada; pool_pre_ping comprueba
# conexiones del pool antes de reutilizarlas. Ninguno sustituye un servicio caído.
engine = create_engine(DB_URL, connect_args={'connect_timeout': 3}, pool_pre_ping=True)
SessionLocal = sessionmaker(engine)


def esperar_bd(intentos=15, pausa=2.0):
    """Espera de arranque: PostgreSQL puede tardar unos segundos en estar listo."""
    for i in range(1, intentos + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[BD] conectada")
            return
        except Exception as error:
            print(f"[BD] no disponible (intento {i}/{intentos}): {error.__class__.__name__}")
            if i < intentos:
                time.sleep(pausa)
    raise RuntimeError("La base de datos no respondió. ¿Está corriendo el contenedor?")
