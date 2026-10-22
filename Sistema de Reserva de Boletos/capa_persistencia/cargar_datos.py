import json
import os
import sys

from sqlalchemy.orm import Session

from capa_persistencia.conexion_bd import engine, esperar_bd
from capa_persistencia.modelos import Base, Evento, Ocurrencia
from capa_persistencia.servicio_persistencia import Servicio_persistencia
from capa_persistencia.utilidades import leer_fecha

RUTA_POR_DEFECTO = os.path.join("datos", "eventos.json")
CAPACIDAD = 100


def generar(ruta, anio=2026, mes=11):
    """Escribe el JSON por defecto: E1..E50; E1..E20 ocurren dos veces (día d y d+14)."""
    eventos = []
    for i in range(1, 51):
        dia = (i - 1) % 14 + 1                         # días 1 a 14
        fechas = [f"{anio}/{mes:02d}/{dia:02d}"]
        if i <= 20:
            fechas.append(f"{anio}/{mes:02d}/{dia + 14:02d}")   # días 15 a 28
        eventos.append({"id": f"E{i}", "nombre": f"Evento {i}",
                        "tipo_evento": "cultural" if i % 2 else "deportivo",
                        "fechas": fechas})
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(eventos, archivo, ensure_ascii=False, indent=2)
    print(f"[CARGA] generado {ruta} con {len(eventos)} eventos")


def cargar(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        datos = json.load(archivo)

    Base.metadata.drop_all(engine)       # empezar de cero: el profesor compara antes y después
    Base.metadata.create_all(engine)

    with Session(engine) as session, session.begin():
        for d in datos:
            evento = Evento(id=d["id"], nombre=d["nombre"], tipo_evento=d["tipo_evento"])
            for texto in d["fechas"]:
                evento.ocurrencias.append(
                    Ocurrencia(fecha=leer_fecha(texto), capacidad=CAPACIDAD, puestos_ocupados=0))
            session.add(evento)
    print(f"[CARGA] {len(datos)} eventos cargados desde {ruta}")


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else RUTA_POR_DEFECTO
    esperar_bd()
    if not os.path.exists(ruta):
        if ruta != RUTA_POR_DEFECTO:
            sys.exit(f"[CARGA] no existe el archivo {ruta}")
        generar(ruta)
    cargar(ruta)
    Servicio_persistencia().imprimir_estado()
