"""Entrada del consumidor: un caso verificable o carga de consulta/reserva.

Se ejecuta con -m desde la carpeta Sistema de Reserva de Boletos. Así Python
encuentra los paquetes comun, capa_consumidores, capa_servicios y capa_persistencia.
"""
import argparse
from datetime import datetime
from capa_consumidores.cliente import Cliente
from capa_consumidores.carga_clientes import carga_automatica


def ejecutar_caso(cliente, mes="noviembre", anio=2026):
    print(f"== 1. Consultar {mes} de {anio} ==")
    consulta = cliente.consultar_evento(mes, anio)
    print(consulta)
    if consulta['estado'] != 'EXITO' or not consulta['datos']['eventos']:
        raise ValueError('No se obtuvieron eventos; revise las capas, el mes y la carga inicial')
    # Elegir una fecha devuelta por la base evita reservar un E1 en una fecha inexistente.
    evento = consulta['datos']['eventos'][0]
    fecha = datetime.strptime(evento['fecha'], '%Y/%m/%d').date()
    print(f"== 2. Reservar 2 puestos en {evento['id_evento']} el {evento['fecha']} ==")
    reserva = cliente.reservar_evento(fecha, evento['id_evento'], 2)
    print(reserva)
    if reserva['estado'] != 'EXITO':
        raise ValueError('La reserva de demostración no se confirmó; revise el motivo y el cupo')
    print("== 3. Pedir más que la capacidad: debe rechazarse SIN_CUPO ==")
    rechazo = cliente.reservar_evento(fecha, evento['id_evento'], evento['capacidad'] + 1)
    print(rechazo)
    if rechazo['motivo'] != 'SIN_CUPO':
        raise ValueError('El rechazo no fue el esperado; revise la respuesta')
    print("== 4. Consultar de nuevo para observar los puestos ocupados ==")
    print(cliente.consultar_evento(mes, anio))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modo', nargs='?', choices=['caso', 'carga'], default='caso')
    parser.add_argument('--id-cliente', type=int, default=1)
    parser.add_argument('--mes', default='noviembre')
    parser.add_argument('--anio', type=int, default=2026)
    parser.add_argument('--rpm', type=float, default=20, help='Solicitudes/minuto por cliente')
    parser.add_argument('--porcentaje-consulta', type=float, default=60)
    parser.add_argument('--minutos', type=float, default=1)
    args = parser.parse_args()
    cliente = Cliente(args.id_cliente)
    cliente.conectar_con_gt()
    try:
        if args.modo == 'caso':
            ejecutar_caso(cliente, args.mes, args.anio)
        else:
            print(carga_automatica(cliente, args.rpm, args.porcentaje_consulta,
                                  args.minutos, args.mes, args.anio))
    except ValueError as error:
        parser.exit(1, f"Error: {error}\n")
    finally:
        cliente.cerrar_socket()
        cliente.terminar_contexto()


# Importar este archivo no ejecuta main. Solo sucede al invocarlo con python -m.
if __name__ == '__main__':
    main()
