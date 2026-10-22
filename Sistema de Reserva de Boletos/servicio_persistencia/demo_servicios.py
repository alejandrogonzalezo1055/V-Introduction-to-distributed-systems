"""Emisores de demostración: simula las llamadas de RMC y cancelaciones por ZeroMQ."""

import argparse
import json

from persistencia.cliente import consultar, reservar, modificar, cancelar


def mostrar(etiqueta, respuesta):
    print(f"\n{etiqueta}")
    print(json.dumps(respuesta, indent=2, ensure_ascii=False))
    if not respuesta["ok"]:
        raise SystemExit("La demostración se detuvo por la respuesta anterior.")
    return respuesta["datos"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direccion", default="tcp://127.0.0.1:5557")
    args = parser.parse_args()
    direccion = args.direccion
    mostrar("RMC consulta disponibilidad", consultar({"tipo": "disponibilidad", "id_evento": "E1", "ocurrencia": 1}, direccion))
    datos = mostrar("RMC reserva 3 puestos", reservar({"id_cliente": 1, "id_evento": "E1", "ocurrencia": 1, "cantidad_asientos": 3}, direccion))
    referencia = {"id_cliente": 1, "id_reserva": datos["reserva"]["id_reserva"]}
    mostrar("RMC consulta la reserva", consultar({**referencia, "tipo": "reserva"}, direccion))
    mostrar("RMC modifica a 5 puestos", modificar({**referencia, "cantidad_asientos": 5}, direccion))
    mostrar("RMC cambia a la segunda fecha", modificar({**referencia, "ocurrencia": 2}, direccion))
    mostrar("Cancelaciones libera la reserva", cancelar(referencia, direccion))
    print("\nPersistencia confirmó la cancelación. El servicio de cancelaciones puede notificar al cliente.")


if __name__ == "__main__":
    main()
