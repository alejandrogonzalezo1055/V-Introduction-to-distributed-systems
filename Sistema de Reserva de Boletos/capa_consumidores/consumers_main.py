import sys
import re
from capa_consumidores.cliente import Cliente



def main():
    regex_fecha = r"\d{4}-\d{2}-\d{2}"

    if len(sys.argv) == 2:
        ...
    elif len(sys.argv) == 1:
        cliente = Cliente(input("Ingrese el nombre del cliente: "))

        while True:
            opcion = int(input("\n1. Consultar eventos\n2. Reservar evento\n0. Salir\n-> "))

            match opcion:
                case 1:
                    mes = input("Ingrese el mes del que quiere conocer los eventos: ")
                    respuesta = cliente.consultar_evento(mes)
                    cliente.procesar_rta(respuesta)
                case 2:
                    id = int(input("Ingrese el id del evento: "))
                    fecha = input("Ingrese la fecha del evento: ")
                    n_asientos = int(input("Ingrese el numero de asientos a reservar: "))
                case 0:
                    break
                case _:
                    print("Opcion incorrecta")


if __name__ == "__main__":
    main()