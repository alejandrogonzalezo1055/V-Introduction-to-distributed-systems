import sys
import re
from capa_consumidores.cliente import Cliente
from datetime import date


def menu(cliente):
    regex_fecha = r"\d{4}-\d{2}-\d{2}"

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
                if re.fullmatch(regex_fecha, fecha):
                    year, month, day = fecha.split("-")
                    respuesta = cliente.reservar_evento(id, date(int(year),int(month),int(day)), n_asientos)
                    cliente.procesar_rta(respuesta)
            case 0:
                break
            case _:
                print("Opcion inexistente")


def main():
    if len(sys.argv) == 2:
        cliente = Cliente()
        cliente.conectar_con_gt()
        opcion = sys.argv[1]

        match opcion:
            case 'nombre':
                cliente.nombre = input("Ingrese el nombre del cliente: ")
                menu(cliente)
    elif len(sys.argv) == 1:
        cliente = Cliente()
        cliente.conectar_con_gt()

        menu(cliente)




if __name__ == "__main__":
    main()