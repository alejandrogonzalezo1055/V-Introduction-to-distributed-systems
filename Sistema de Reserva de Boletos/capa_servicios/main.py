import sys
import zmq
import comun.mensajes as msjs
from comun.config import HOST_SERV, GT_PORT_RMC
from capa_servicios.gestor_transacciones.gestor_de_transacciones import Gestor_transacciones
from capa_servicios.servicio_RMC.servicio_rmc import Servicio_RMC, Cliente_persistencia


def arrancar_gt():
    gt = Gestor_transacciones()
    gt.iniciar_sockets()
    print("[GT] listo, esperando clientes y RMC")
    try:
        gt.iniciar_gestor()
    except KeyboardInterrupt:
        print("[GT] detenido")
    finally:
        gt.router_socket.close(linger=0)
        gt.dealer_socket.close(linger=0)
        gt.contexto.term()


def arrancar_rmc():
    contexto = zmq.Context()
    socket_gt = contexto.socket(zmq.REP)
    socket_gt.connect(f"tcp://{HOST_SERV}:{GT_PORT_RMC}")

    servicio = Servicio_RMC(Cliente_persistencia())

    # tipo de petición -> método del servicio que la atiende
    operaciones = {
        msjs.peticiones['CO']: servicio.consultar_eventos,
        msjs.peticiones['R']: servicio.crear_reserva,
        msjs.peticiones['M']: servicio.modificar_reserva,
    }

    print("[RMC] listo, conectado al GT")
    try:
        while True:
            texto = socket_gt.recv_string()
            try:
                peticion = msjs.decodificar(texto)
                print(f"[RMC] <- {peticion['tipo']} {peticion['uuid']}")
                operacion = operaciones.get(peticion['tipo'])
                if operacion is None:
                    respuesta = msjs.crear_rta('ER', 'P_I', {'razon': f"tipo desconocido: {peticion['tipo']}"})
                else:
                    respuesta = operacion(peticion)
            except Exception as error:
                # pase lo que pase, el REP SIEMPRE debe responder
                respuesta = msjs.crear_rta('ER', 'P_I', {'razon': str(error)})

            print(f"[RMC] -> {respuesta}")
            socket_gt.send_string(msjs.codificar(respuesta))
    except KeyboardInterrupt:
        print("[RMC] detenido")
    finally:
        socket_gt.close(linger=0)
        contexto.term()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("gt", "rmc"):
        print("uso: python -m capa_servicios.main [gt|rmc]")
        sys.exit(1)

    if sys.argv[1] == "gt":
        arrancar_gt()
    else:
        arrancar_rmc()