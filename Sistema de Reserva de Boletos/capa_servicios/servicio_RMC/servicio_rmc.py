from abc import ABC, abstractmethod

class I_Servicio_RMC(ABC):
    @abstractmethod
    def crear_reserva(self, peticion):
        pass

    @abstractmethod
    def modificar_reserva(self, peticion):
        pass

    @abstractmethod
    def consultar_reserva(self, peticion):
        pass

class Servicio_RMC(I_Servicio_RMC):
    ...