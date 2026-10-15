"""Funciones que RMC y cancelaciones importan para comunicarse con persistencia."""

import argparse
import json
from pathlib import Path
import uuid

import zmq

from persistencia.protocolo import respuesta_error

DIRECCION = "tcp://127.0.0.1:5557"


def enviar_peticion(peticion, direccion=DIRECCION, timeout_ms=8000):
    """Envía JSON por REQ y espera la respuesta ROUTER. No reintenta escrituras."""
    if not isinstance(peticion, dict):
        raise ValueError("La petición debe ser un diccionario.")
    if type(timeout_ms) is not int or timeout_ms <= 0:
        raise ValueError("timeout_ms debe ser un entero positivo.")
    mensaje = dict(peticion)
    mensaje.setdefault("id", str(uuid.uuid4()))
    socket = zmq.Context.instance().socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
    socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
    socket.connect(direccion)
    try:
        socket.send_json(mensaje)
        respuesta = socket.recv_json()
        if not isinstance(respuesta, dict) or respuesta.get("id") != mensaje["id"]:
            return respuesta_error("RESPUESTA_INVALIDA", "La respuesta no corresponde a la petición.",
                                   mensaje["id"], mensaje.get("operacion"))
        return respuesta
    except zmq.Again:
        return respuesta_error("TIEMPO_AGOTADO", "No llegó respuesta; el resultado puede ser incierto.",
                               mensaje["id"], mensaje.get("operacion"))
    finally:
        socket.close()


def consultar(datos, direccion=DIRECCION):
    return enviar_peticion({**datos, "operacion": "consulta"}, direccion)


def reservar(datos, direccion=DIRECCION):
    return enviar_peticion({**datos, "operacion": "reserva"}, direccion)


def modificar(datos, direccion=DIRECCION):
    return enviar_peticion({**datos, "operacion": "modificacion"}, direccion)


def cancelar(datos, direccion=DIRECCION):
    return enviar_peticion({**datos, "operacion": "cancelacion"}, direccion)


def main():
    parser = argparse.ArgumentParser(description="Enviar un JSON como lo harían RMC o cancelaciones")
    parser.add_argument("archivo", type=Path)
    parser.add_argument("--direccion", default=DIRECCION)
    args = parser.parse_args()
    peticion = json.loads(args.archivo.read_text(encoding="utf-8"))
    respuesta = enviar_peticion(peticion, args.direccion)
    print(json.dumps(respuesta, ensure_ascii=False, indent=2))
    if not respuesta["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
