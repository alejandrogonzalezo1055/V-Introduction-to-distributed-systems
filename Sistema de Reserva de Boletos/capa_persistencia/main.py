"""Proceso de Persistencia: socket REP con bind en SP_PUERTO.

Uso (desde la raíz del proyecto):  python -m capa_almacenamiento.main
"""
import zmq

import comun.mensajes as msjs
from comun.config import SP_PORT
from capa_almacenamiento.conexion_bd import esperar_bd
from capa_almacenamiento.servicio_persistencia import (
    ERROR, PETICION_INVALIDA, DATO_INVALIDO, Servicio_persistencia, responder,
)


def main():
    esperar_bd()
    servicio = Servicio_persistencia()
    servicio.imprimir_estado()                    # estado inicial de la BD

    # tipo de petición -> método que la atiende
    operaciones = {
        msjs.peticiones['CO']: servicio.consultar_eventos,
        msjs.peticiones['CO_D']: servicio.consultar_disponibilidad,
        msjs.peticiones['A_R']: servicio.agregar_reserva,
        msjs.peticiones['M']: servicio.modificar_reserva,
        msjs.peticiones['CA']: servicio.eliminar_reserva,
    }

    contexto = zmq.Context()
    socket = contexto.socket(zmq.REP)
    socket.bind(f"tcp://*:{SP_PORT}")
    print(f"[PERSISTENCIA] escuchando en :{SP_PORT}")

    try:
        while True:
            texto = socket.recv_string()
            peticion = {}
            try:
                peticion = msjs.decodificar(texto)
                tipo = peticion.get('tipo')
                print(f"[PERSISTENCIA] <- {tipo} {peticion.get('datos')}")
                operacion = operaciones.get(tipo)
                if operacion is None:
                    respuesta = responder(peticion, ERROR, PETICION_INVALIDA,
                                          {'razon': f'tipo desconocido: {tipo}'})
                else:
                    respuesta = operacion(peticion)
            except Exception as error:
                # pase lo que pase, el REP SIEMPRE responde; si no, el RMC queda colgado
                respuesta = responder(peticion, ERROR, DATO_INVALIDO, {'razon': str(error)})

            print(f"[PERSISTENCIA] -> {respuesta['estado']} {respuesta['motivo'] or ''} {respuesta['datos']}")
            socket.send_string(msjs.codificar(respuesta))
    except KeyboardInterrupt:
        print("[PERSISTENCIA] detenido")
        servicio.imprimir_estado()                # estado final de la BD
    finally:
        socket.close(linger=0)
        contexto.term()


if __name__ == "__main__":
    main()
