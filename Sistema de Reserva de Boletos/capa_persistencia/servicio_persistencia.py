from abc import ABC, abstractmethod
from sqlalchemy import create_engine, text
from comun.config import DB_URL


class I_Servicio_Persistencia(ABC):
    @abstractmethod
    def agregar_reserva(self, peticion):
        pass

    @abstractmethod
    def consultar_reserva(self, peticion):
        pass

    @abstractmethod
    def modificar_reserva(self, peticion):
        pass

    @abstractmethod
    def eliminar_reserva(self, peticion):
        pass


class Servicio_Persistencia(I_Servicio_Persistencia):
    def __init__(self):
        self.engine = create_engine(DB_URL, echo=True)

    @property
    def engine(self):
        return self._engine

    @engine.setter
    def engine(self, engine):
        self._engine = engine

    def conectar_con_bd(self):
        with self.engine.connect() as conn:
            print(conn.execute(text("SELECT version()")).scalar_one())

    def agregar_reserva(self, peticion):
        ...

    def consultar_reserva(self, peticion):
        ...

    def modificar_reserva(self, peticion):
        ...

    def eliminar_reserva(self, peticion):
        ...