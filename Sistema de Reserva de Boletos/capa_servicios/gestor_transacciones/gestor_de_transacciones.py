"""Puente de mensajes: cliente REQ -> ROUTER/DEALER del GT -> RMC REP.

El GT conserva todos los frames. ROUTER añade la identidad de conexión del cliente
y REP la conserva internamente para responder. El UUID dentro del JSON identifica
la petición de negocio; la identidad del frame permite devolverla a su socket.
"""
import zmq
from comun.config import GT_PORT_CLI, GT_PORT_RMC

class Gestor_transacciones():
    def __init__(self):
        self.dealer_socket = None
        self.router_socket = None
        self.contexto = None
        self.poller = None

    @property
    def contexto(self):
        # Las propiedades conservan el diseño: lectura pública, almacenamiento _privado.
        return self._contexto

    @contexto.setter
    def contexto(self, contexto):
        self._contexto = contexto

    @property
    def dealer_socket(self):    # el del RMC
        return self._dealer_socket

    @dealer_socket.setter
    def dealer_socket(self, dealer_socket):
        self._dealer_socket = dealer_socket

    @property
    def router_socket(self):    # el del CLIENTE
        return self._router_socket

    @router_socket.setter
    def router_socket(self, router_socket):
        self._router_socket = router_socket

    @property
    def poller(self):
        return self._poller

    @poller.setter
    def poller(self, poller):
        self._poller = poller


    def iniciar_sockets(self):
        # bind('*') escucha por las interfaces de esta máquina. Nunca usar '*' en connect.
        self.contexto = zmq.Context()
        self.router_socket = self.contexto.socket(zmq.ROUTER)
        self.router_socket.bind(f"tcp://*:{GT_PORT_CLI}")
        self.dealer_socket = self.contexto.socket(zmq.DEALER)
        self.dealer_socket.bind(f"tcp://*:{GT_PORT_RMC}")
        self.poller = zmq.Poller()
        # Poller indica cuál socket tiene mensajes sin bloquear esperando solo uno.
        self.poller.register(self.dealer_socket, zmq.POLLIN)
        self.poller.register(self.router_socket, zmq.POLLIN)

    def iniciar_gestor(self):
        while True:
            # Espera hasta que llegue una petición del cliente o respuesta del RMC.
            sockets = dict(self.poller.poll())

            if self.dealer_socket in sockets and sockets[self.dealer_socket] == zmq.POLLIN:
                frames = self.dealer_socket.recv_multipart()
                print(f"[GT] respuesta: {frames[-1]!r}", flush=True)
                # Respuesta completa: [identidad_cliente, separador vacío, JSON].
                self.router_socket.send_multipart(frames)
            if self.router_socket in sockets and sockets[self.router_socket] == zmq.POLLIN:
                frames = self.router_socket.recv_multipart()
                print(f"[GT] petición: {frames[-1]!r}", flush=True)
                # No reenviar únicamente el JSON: se perdería la ruta al consumidor.
                self.dealer_socket.send_multipart(frames)

