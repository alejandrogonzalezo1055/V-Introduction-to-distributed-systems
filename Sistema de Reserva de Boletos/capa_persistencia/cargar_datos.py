"""Carga administrativa: prepara datos iniciales antes de arrancar persistencia.

La carga normal protege una base que ya contiene datos. Solo --reiniciar permite
borrar y recrear las tablas para repetir conscientemente un experimento.
"""
import argparse
import json
import os
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session
from capa_persistencia.conexion_bd import engine, esperar_bd
from capa_persistencia.modelos import Base, Evento, Ocurrencia
from capa_persistencia.servicio_persistencia import Servicio_persistencia
from capa_persistencia.utilidades import leer_fecha

RUTA_POR_DEFECTO = os.path.join('datos', 'eventos.json')
CAPACIDAD = 100


def generar(ruta, anio=2026, mes=11):
    """Genera 50 eventos y 70 ocurrencias del mismo mes: 20 dobles y 30 simples."""
    eventos = []
    for i in range(1, 51):
        dia = (i - 1) % 14 + 1  # Primeras fechas entre día 1 y 14.
        fechas = [f"{anio}/{mes:02d}/{dia:02d}"]
        if i <= 20:
            fechas.append(f"{anio}/{mes:02d}/{dia + 14:02d}")  # Segundas: día 15-28.
        eventos.append({'id': f'E{i}', 'nombre': f'Evento {i}',
                        'tipo_evento': 'cultural' if i % 2 else 'deportivo', 'fechas': fechas})
    os.makedirs(os.path.dirname(ruta) or '.', exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as archivo:
        json.dump(eventos, archivo, ensure_ascii=False, indent=2)
    print(f"[CARGA] generado {ruta} con {len(eventos)} eventos")


def cargar(ruta, reiniciar=False):
    with open(ruta, encoding='utf-8') as archivo:
        datos = json.load(archivo)
    # Validar el archivo completo antes de cualquier borrado de tablas.
    if not isinstance(datos, list) or not datos:
        raise ValueError('El archivo debe contener una lista no vacía de eventos')
    ids = set()
    for dato in datos:
        if not isinstance(dato.get('id'), str) or not 1 <= len(dato['id']) <= 10 or dato['id'] in ids:
            raise ValueError('Cada evento necesita un id de texto único de 1 a 10 caracteres')
        ids.add(dato['id'])
        if not dato.get('nombre') or not dato.get('tipo_evento') or not dato.get('fechas'):
            raise ValueError('Faltan nombre, tipo_evento o fechas de un evento')
        fechas = [leer_fecha(texto) for texto in dato['fechas']]
        if len(set(fechas)) != len(fechas):
            raise ValueError('Un evento no puede repetir la misma fecha')
    if not reiniciar and inspect(engine).has_table('evento'):
        with Session(engine) as session:
            if session.scalar(select(func.count()).select_from(Evento)):
                raise ValueError('La base ya contiene eventos. Use --reiniciar solo si desea borrarlos')
    if reiniciar:
        Base.metadata.drop_all(engine)  # Borrado explícito y administrativo, nunca por petición de un cliente.
    Base.metadata.create_all(engine)
    # Session.begin confirma todos los eventos juntos o revierte la carga completa.
    with Session(engine) as session, session.begin():
        for dato in datos:
            evento = Evento(id=dato['id'], nombre=dato['nombre'], tipo_evento=dato['tipo_evento'])
            for texto in dato['fechas']:
                evento.ocurrencias.append(Ocurrencia(fecha=leer_fecha(texto),
                                                    capacidad=CAPACIDAD, puestos_ocupados=0))
            session.add(evento)
    print(f"[CARGA] {len(datos)} eventos cargados desde {ruta}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ruta', nargs='?', default=RUTA_POR_DEFECTO)
    parser.add_argument('--reiniciar', action='store_true', help='BORRAR tablas y cargar nuevamente')
    args = parser.parse_args()
    esperar_bd()
    try:
        if not os.path.exists(args.ruta):
            if args.ruta != RUTA_POR_DEFECTO:
                parser.error(f'No existe el archivo {args.ruta}')
            generar(args.ruta)
        cargar(args.ruta, reiniciar=args.reiniciar)
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        parser.error(str(error))
    Servicio_persistencia().imprimir_estado()


if __name__ == '__main__':
    main()
