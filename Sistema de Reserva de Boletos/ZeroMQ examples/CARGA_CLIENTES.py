import json
import zmq
import time
import random
lista_meses = ["septiembre", "octubre", "noviembre"]
dir_gestor="" 
ID_cliente=1
solicitudes_minuto=20
porcentaje_consulta=60


def conectar_gestor():
    contexto=zmq.context() #creo el canal síncrono
    socket= contexto.socket(zmq.REQ) #creo un socket de tipo REQ
    socket.connect(dir_gestor)
    return socket
def enviar_peticion(socket,diccionario_datos):
    mensaje_texto=json.dumps(diccionario_datos)#lo convierto en un texto plano
    socket.send_string(mensaje_texto) # envío un texto hacia el GT
    respuesta_texto=socket.recv_string()#recibo la rta del GT
    respuesta_dic=json.loads(respuesta_texto)#convierto la rta en un formato JSON

    return respuesta_dic

def consulta_eventos(socket,id_cliente,mes):
    solicitud={
            "operacion":"consulta",
            "id_cliente":id_cliente,
            "mes":mes
            }
    print(f"{id_cliente} enviando solicitud")

    respuesta=enviar_peticion(socket,solicitud)

    print(f"{id_cliente} respuesta recibida: {respuesta}")

    return respuesta;

def reservar_asientos(socket,id_cliente, id_evento, cantidad_asientos):
    solicitud={
            "operacion":"reserva",
            "id_cliente":id_cliente,
            "id_evento":id_evento,
            "ocurrencia":ocurrencia,
            "cantidad_asientos":cantidad_asientos
            }
    respuesta=enviar_peticion(socket,solicitud)
    print(f"{id_cliente} la solicitud ha sido enviada con: \n ocurrencia:{ocurrencia} \n cantidad de asientos:{cantidad_asientos}")
    print(f"respuesta del GT: {respuesta}")
    return respuesta

def ejecutar_caso_especifico(socket,id_cliente):

    consultar_eventos(socket,id_cliente,"Noviembre")
    reservar_asientos(socket,id_cliente,id_evento="E1",cantidad_asientos=5,ocurrencia=1)

    print("Caso finalizado")

def carga_automatica(socket,id_cliente,duracion_minutos=1):
    pausa_clientes=60.0/solicitudes_minuto 
    peticiones_totales=solicitudes_minuto*duracion_minutos


    for numero i in range(1,peticiones_totales+1)
    azar=random.randint(1,100)

    if azar<=porcentaje_consulta :
        random_mes=random.choice(lista_meses)

        consulta_eventos(socket,id_cliente,random_mes)
    else:
        evento_random=f"E{random.randint(1,50)}"
        asientos_azar=random.randint(1,4)
        reservar_asientos(socket,id_cliente,evento_random,asientos_azar,ocurrencia=1)

    time.sleep(pausa_clientes)


if __name__ == "__main__":
    contexto, mi_socket = conectar_al_gestor()

    try:
        #ejecutar_caso_especifico(mi_socket,id_cliente)
        carga_automatica(socket,id_cliente,duracion_minutos=1)

    finally:
        mi_socket.close()
        contexto.term()




          





