"""Punto de entrada de negocio: ejecutar GT y RMC en terminales independientes.

python -m capa_servicios.main gt
python -m capa_servicios.main rmc
Ambos viven en la máquina de la capa de servicios cuando se despliega en tres VM.
"""
import sys
import zmq
import comun.mensajes as msjs
from comun.config import HOST_SERV, GT_PORT_RMC
from capa_servicios.gestor_transacciones.gestor_de_transacciones import Gestor_transacciones
from capa_servicios.servicio_RMC.servicio_rmc import Servicio_RMC, Cliente_persistencia


def arrancar_gt():
    gt = Gestor_transacciones()
    gt.iniciar_sockets()
    print("[GT] listo, esperando clientes y RMC", flush=True)
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
    socket_gt.setsockopt(zmq.LINGER, 0)
    # El GT hace bind del DEALER. El RMC se conecta con REP: recibe un mensaje
    # y debe devolver exactamente una respuesta, incluso si rechaza la petición.
    socket_gt.connect(f"tcp://{HOST_SERV}:{GT_PORT_RMC}")
    mensajero = Cliente_persistencia()
    servicio = Servicio_RMC(mensajero)
    operaciones = {
        msjs.peticiones['CO']: servicio.consultar_eventos,
        msjs.peticiones['R']: servicio.crear_reserva,
        msjs.peticiones['M']: servicio.modificar_reserva,
    }
    print(f"[RMC] conectado al GT en {HOST_SERV}:{GT_PORT_RMC}", flush=True)
    try:
        while True:
            # Recibir bytes y decodificar dentro del try también captura UTF-8 roto.
            texto = socket_gt.recv()
            peticion = {}
            try:
                peticion = msjs.decodificar(texto)
                msjs.validar_peticion(peticion)
                print(f"[RMC] <- {peticion['tipo']} {peticion['uuid']}", flush=True)
                operacion = operaciones.get(peticion['tipo'])
                if operacion is None:
                    respuesta = msjs.crear_rta('ER', 'P_I', {'razon': 'Tipo no atendido por RMC'}, peticion['uuid'])
                else:
                    respuesta = operacion(peticion)
            except (ValueError, TypeError, KeyError) as error:
                identificador = peticion.get('uuid', '') if isinstance(peticion, dict) else ''
                respuesta = msjs.crear_rta('ER', 'P_I', {'razon': str(error)}, identificador)
            except Exception:
                identificador = peticion.get('uuid', '') if isinstance(peticion, dict) else ''
                respuesta = msjs.crear_rta('ER', 'P_I', {'razon': 'Error interno en RMC; revisar el proceso'}, identificador)
            print(f"[RMC] -> {respuesta}", flush=True)
            socket_gt.send_string(msjs.codificar(respuesta))
    except KeyboardInterrupt:
        print("[RMC] detenido")
    finally:
        mensajero.cerrar()
        socket_gt.close(linger=0)
        contexto.term()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("gt", "rmc"):
        sys.exit("uso: python -m capa_servicios.main [gt|rmc]")
    if sys.argv[1] == "gt":
        arrancar_gt()
    else:
        arrancar_rmc()
