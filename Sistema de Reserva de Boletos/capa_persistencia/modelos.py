from sqlalchemy import String, Integer, Date
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.testing.schema import mapped_column


class Base(DeclarativeBase):
    pass

class Evento(Base):
    __tablename__ = "evento"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    tipo_evento: Mapped[str] = mapped_column(String(30))


class Ocurrencia(Base):
    __tablename__ = "ocurrencia"

    capacidad: Mapped[int] = mapped_column(Integer)
    puestos_ocupados: Mapped[int] = mapped_column(Integer)
    fecha: Mapped[Date] = mapped_column(Date)
