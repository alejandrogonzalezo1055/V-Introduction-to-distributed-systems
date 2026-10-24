import zmq
from comun.config import GT_PORT_CLI, GT_PORT_RMC


class Gestor_transacciones():
    def __init__(self):
        self.dealer_socket = None
        self.router_socket = None
        self.poller = None

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
        self.router_socket = zmq.Context().socket(zmq.ROUTER)
        self.router_socket.bind(f"tcp://*:{GT_PORT_CLI}")
        self.dealer_socket = zmq.Context().socket(zmq.DEALER)
        self.dealer_socket.bind(f"tcp://*:{GT_PORT_RMC}")


    def iniciar_poller(self):
        self.poller = zmq.Poller()
        self.poller.register(self.dealer_socket, zmq.POLLIN)
        self.poller.register(self.router_socket, zmq.POLLIN)


    def iniciar_gestor(self):
        while True:
            sockets = dict(self.poller.poll())

            if self.dealer_socket in sockets and sockets[self.dealer_socket] == zmq.POLLIN:
                frames = self.dealer_socket.recv_multipart()
                print(f"la respuesta es: {frames[-1].decode('utf-8')}")
                self.router_socket.send_multipart(frames)
            if self.router_socket in sockets and sockets[self.router_socket] == zmq.POLLIN:
                frames = self.router_socket.recv_multipart()
                print(f"la peticion es: {frames[-1].decode('utf-8')}")
                self.dealer_socket.send_multipart(frames)