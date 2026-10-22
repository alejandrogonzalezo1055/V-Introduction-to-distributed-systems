import sys
import zmq
from datetime import date
from capa_consumidores.cliente import Cliente
from capa_consumidores.carga_clientes import carga_automatica

ID_CLIENTE = 1


def ejecutar_caso(cliente):
    # AJUSTA evento y fecha a uno que exista en sus datos iniciales
    print("== 1. Consulta de eventos de noviembre ==")
    print(cliente.consultar_evento("noviembre"))

    print("== 2. Reserva válida ==")
    print(cliente.reservar_evento(date(2026, 11, 7), "E1", 2))

    print("== 3. Reserva imposible (101 puestos, debe ser rechazada) ==")
    print(cliente.reservar_evento(date(2026, 11, 7), "E1", 101))

    print("== 4. Consulta otra vez, para ver que subieron los ocupados ==")
    print(cliente.consultar_evento("noviembre"))


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "caso"

    cliente = Cliente(ID_CLIENTE)
    cliente.conectar_con_gt()
    try:
        if modo == "caso":
            ejecutar_caso(cliente)
        elif modo == "carga":
            carga_automatica(cliente, 20, 60, 1)
        else:
            print("uso: python -m capa_consumidores.main [caso|carga]")
    except zmq.Again:
        print("Timeout: no llegó respuesta. ¿Están corriendo el GT, el RMC y Persistencia?")
    finally:
        cliente.cerrar_socket()
        cliente.terminar_contexto()


if __name__ == "__main__":
    main()