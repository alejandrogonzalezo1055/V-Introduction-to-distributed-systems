"""Carga configurable de consulta/reserva, sin conexiones al importar el módulo."""
import time
import random
from datetime import datetime
from capa_consumidores.cliente import Cliente
from comun.mensajes import meses


def ejecutar_caso_especifico(cliente):
    # Reutiliza el caso de main para no mantener dos demostraciones contradictorias.
    from capa_consumidores.main import ejecutar_caso
    ejecutar_caso(cliente)


def carga_automatica(cliente, sol_minuto, porcen_cons, duracion_minutos=1,
                     mes='noviembre', anio=2026):
    """Un cliente envía una petición a la vez, con ritmo objetivo configurable.

    La consulta inicial obtiene fechas existentes y queda fuera de la ventana de
    carga. Un ritmo alto es un objetivo: si las respuestas tardan, puede no lograrse.
    """
    if sol_minuto <= 0 or duracion_minutos <= 0 or not 0 <= porcen_cons <= 100:
        raise ValueError('Revise rpm > 0, minutos > 0 y porcentaje entre 0 y 100')
    mes = str(mes).strip().lower()
    if mes not in meses or type(anio) is not int or not 1 <= anio <= 9999:
        raise ValueError('Mes o año inválido')
    consulta = cliente.consultar_evento(mes, anio)
    if consulta['estado'] != 'EXITO':
        raise ValueError(f"La consulta inicial falló: {consulta['motivo']}")
    eventos = consulta['datos']['eventos']
    if not eventos and porcen_cons < 100:
        raise ValueError('No hay eventos en ese mes para generar reservas válidas')
    pausa = 60.0 / sol_minuto
    duracion = duracion_minutos * 60
    inicio = time.perf_counter()  # Reloj monotónico: sirve para medir intervalos.
    numero = 0
    resumen = {'enviadas': 0, 'exitos': 0, 'fallos': 0, 'errores': 0}
    while numero * pausa < duracion:
        time.sleep(max(0, inicio + numero * pausa - time.perf_counter()))
        if time.perf_counter() - inicio >= duracion:
            break
        antes = time.perf_counter()
        if random.random() * 100 < porcen_cons:
            tipo = 'CONSULTA'
            respuesta = cliente.consultar_evento(mes, anio)
        else:
            tipo = 'RESERVA'
            evento = random.choice(eventos)
            fecha = datetime.strptime(evento['fecha'], '%Y/%m/%d').date()
            respuesta = cliente.reservar_evento(fecha, evento['id_evento'], random.randint(1, 4))
        numero += 1
        resumen['enviadas'] += 1
        clave = {'EXITO': 'exitos', 'FALLO': 'fallos', 'ERROR': 'errores'}[respuesta['estado']]
        resumen[clave] += 1
        print(f"[CLIENTE {cliente.ID}] {tipo} {respuesta['uuid']} {respuesta['estado']} "
              f"{respuesta['motivo']} {(time.perf_counter() - antes) * 1000:.2f} ms", flush=True)
        if respuesta['motivo'] == 'TIEMPO_AGOTADO':
            # Parar evita acumular escrituras inciertas durante una desconexión.
            raise ValueError('Carga detenida por timeout; revisar servicios y estado antes de continuar')
    time.sleep(max(0, inicio + duracion - time.perf_counter()))
    resumen['segundos'] = round(time.perf_counter() - inicio, 3)
    return resumen


def main_carga():
    cliente = Cliente(1)
    cliente.conectar_con_gt()
    try:
        print(carga_automatica(cliente, 20, 60, 1))
    finally:
        cliente.cerrar_socket()
        cliente.terminar_contexto()


# Antes se llamaba incondicionalmente: importar carga_clientes iniciaba una carga
# y podía bloquear main antes de que el usuario eligiera siquiera un modo.
if __name__ == '__main__':
    main_carga()
