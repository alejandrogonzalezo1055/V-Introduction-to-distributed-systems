import time
import random
from capa_consumidores.cliente import Cliente
from datetime import date, timedelta
from comun.mensajes import meses


def ejecutar_caso_especifico(cliente):

    cliente.consultar_evento("noviembre")
    cliente.reservar_evento(date(2026,10,20), 'E1', 5)

    print("Caso finalizado")


def carga_automatica(cliente,sol_minuto,porcen_cons, duracion_minutos=1):
    pausa_clientes = 60.0/sol_minuto
    peticiones_totales = sol_minuto*duracion_minutos


    for i in range(1,peticiones_totales+1):
        azar=random.randint(1,100)

        if azar <= porcen_cons :
            random_mes = random.choice(meses)
            cliente.consultar_evento(random_mes)
        else:
            evento_random = f"E{random.randint(1,50)}"
            asientos_azar = random.randint(1,4)
            cliente.reservar_evento(fecha_random(), evento_random, asientos_azar)

        time.sleep(pausa_clientes)


def fecha_random():
    fecha_inicio = date(2026, 1, 1)
    fecha_fin = date(2026, 1, 31)

    # 2. Calcula la diferencia total de días entre ambas
    diferencia_en_dias = (fecha_fin - fecha_inicio).days

    # 3. Elige un número de días aleatorio en ese rango
    dias_aleatorios = random.randint(0, diferencia_en_dias)

    # 4. Suma los días aleatorios a la fecha de inicio
    return fecha_inicio + timedelta(days=dias_aleatorios)


def main_carga():
    sol_minuto = 20
    porcen_cons = 60

    # inicializa el cliente con id 1
    cliente = Cliente(1)
    cliente.conectar_con_gt()

    try:
        # ejecutar_caso_especifico(mi_socket,id_cliente)
        carga_automatica(cliente, sol_minuto, porcen_cons, 1)

    finally:
        cliente.cerrar_socket()
        cliente.terminar_contexto()

main_carga()




          





