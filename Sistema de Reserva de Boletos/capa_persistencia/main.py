"""Proceso REP de persistencia; ejecutar desde Sistema de Reserva de Boletos.

python -m capa_persistencia.main          -> servidor para recibir al RMC
python -m capa_persistencia.main --estado -> foto administrativa de la base
"""
import argparse
import zmq
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
import comun.mensajes as msjs
from comun.config import SP_PORT
from capa_persistencia.conexion_bd import engine, esperar_bd
from capa_persistencia.servicio_persistencia import (
    ERROR, PETICION_INVALIDA, Servicio_persistencia, responder,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--estado', action='store_true', help='Mostrar la BD sin abrir otro servidor')
    args = parser.parse_args()
    esperar_bd()
    if not inspect(engine).has_table('reserva'):
        parser.exit(1, 'Faltan las tablas. Ejecute python -m capa_persistencia.cargar_datos\n')
    servicio = Servicio_persistencia()
    servicio.imprimir_estado()
    if args.estado:
        return
    operaciones = {
        msjs.peticiones['CO']: servicio.consultar_eventos,
        msjs.peticiones['CO_D']: servicio.consultar_disponibilidad,
        msjs.peticiones['A_R']: servicio.agregar_reserva,
        msjs.peticiones['M']: servicio.modificar_reserva,
        msjs.peticiones['CA']: servicio.eliminar_reserva,
    }
    contexto = zmq.Context()
    socket = contexto.socket(zmq.REP)
    socket.setsockopt(zmq.LINGER, 0)
    socket.bind(f"tcp://*:{SP_PORT}")
    print(f"[PERSISTENCIA] escuchando en :{SP_PORT}", flush=True)
    try:
        while True:
            texto = socket.recv()
            peticion = {}
            try:
                peticion = msjs.decodificar(texto)
                msjs.validar_peticion(peticion)
                tipo = peticion['tipo']
                print(f"[PERSISTENCIA] <- {tipo} {peticion['uuid']} {peticion['datos']}", flush=True)
                operacion = operaciones.get(tipo)
                if operacion is None:
                    respuesta = responder(peticion, ERROR, PETICION_INVALIDA, {'razon': 'Tipo no atendido por persistencia'})
                else:
                    respuesta = operacion(peticion)
            except (ValueError, TypeError, KeyError) as error:
                respuesta = responder(peticion, ERROR, PETICION_INVALIDA, {'razon': str(error)})
            except SQLAlchemyError as error:
                # La transacción ya revirtió cambios. No incluir credenciales SQL en la respuesta.
                print(f"[PERSISTENCIA] error de BD: {type(error).__name__}", flush=True)
                respuesta = responder(peticion, ERROR, msjs.motivos_rechazo['E_BD'], {'razon': 'Error de base de datos'})
            except Exception:
                respuesta = responder(peticion, ERROR, PETICION_INVALIDA, {'razon': 'Error interno en persistencia'})
            # REP siempre responde, también ante rechazo; si no, no puede recibir otra petición.
            print(f"[PERSISTENCIA] -> {respuesta}", flush=True)
            socket.send_string(msjs.codificar(respuesta))
    except KeyboardInterrupt:
        print("[PERSISTENCIA] detenido")
        servicio.imprimir_estado()
    finally:
        socket.close(linger=0)
        contexto.term()
        engine.dispose()  # Devuelve/cierra las conexiones SQL del pool al salir.


if __name__ == '__main__':
    main()
