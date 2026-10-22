"""Crea PostgreSQL temporal, ejecuta pruebas reales y elimina el contenedor al terminar."""

import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid

import psycopg


def main():
    nombre = "srb-persistencia-pruebas-" + uuid.uuid4().hex[:10]
    clave = secrets.token_hex(20)
    entorno = {**os.environ, "POSTGRES_PASSWORD": clave}
    creado = False
    try:
        subprocess.run(["docker", "run", "--rm", "--detach", "--name", nombre,
                        "--publish", "127.0.0.1::5432", "--tmpfs", "/var/lib/postgresql/data",
                        "--env", "POSTGRES_PASSWORD", "--env", "POSTGRES_DB=srb_pruebas",
                        "postgres:17-alpine"], env=entorno, check=True, capture_output=True, text=True)
        creado = True
        puerto = subprocess.check_output(["docker", "port", nombre, "5432/tcp"], text=True).strip().rsplit(":", 1)[1]
        url = f"postgresql://postgres:{clave}@127.0.0.1:{puerto}/srb_pruebas"
        limite = time.monotonic() + 40
        while True:
            try:
                with psycopg.connect(url, connect_timeout=1):
                    break
            except psycopg.OperationalError:
                if time.monotonic() >= limite:
                    raise RuntimeError("PostgreSQL temporal no estuvo listo en 40 segundos")
                time.sleep(.25)
        print("Ejecutando pruebas contra PostgreSQL temporal, sin usar las bases del proyecto.", flush=True)
        resultado = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                                   cwd=Path(__file__).parent,
                                   env={**os.environ, "SRB_TEST_DATABASE_URL": url})
        return resultado.returncode
    finally:
        if creado:
            subprocess.run(["docker", "stop", "--time", "2", nombre], check=True, capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
