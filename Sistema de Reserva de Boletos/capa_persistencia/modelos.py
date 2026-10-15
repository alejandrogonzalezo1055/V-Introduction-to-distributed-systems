"""Entidades del modelo del mundo mapeadas a tablas con SQLAlchemy ORM.

Solo el proceso de Persistencia importa este archivo. Lo que viaja por
ZeroMQ son diccionarios, nunca estos objetos.
"""
from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Evento(Base):
    __tablename__ = "evento"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)    # "E1", "E2", ...
    nombre: Mapped[str] = mapped_column(String(120))
    tipo_evento: Mapped[str] = mapped_column(String(30))

    ocurrencias: Mapped[list["Ocurrencia"]] = relationship(back_populates="evento")


class Ocurrencia(Base):
    __tablename__ = "ocurrencia"
    __table_args__ = (
        # el RMC identifica una ocurrencia por (evento, fecha): no se puede repetir
        UniqueConstraint("evento_id", "fecha", name="uq_evento_fecha"),
        # red de seguridad: la base rechaza cualquier sobreventa
        CheckConstraint("puestos_ocupados >= 0 AND puestos_ocupados <= capacidad", name="ck_cupo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evento_id: Mapped[str] = mapped_column(ForeignKey("evento.id"))
    fecha: Mapped[date]
    capacidad: Mapped[int] = mapped_column(default=100)
    puestos_ocupados: Mapped[int] = mapped_column(default=0)

    evento: Mapped["Evento"] = relationship(back_populates="ocurrencias")
    reservas: Mapped[list["Reserva"]] = relationship(back_populates="ocurrencia")


class Reserva(Base):
    __tablename__ = "reserva"
    __table_args__ = (
        CheckConstraint("numero_puestos > 0", name="ck_numero_puestos"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    id_cliente: Mapped[int]
    ocurrencia_id: Mapped[int] = mapped_column(ForeignKey("ocurrencia.id"))
    numero_puestos: Mapped[int]
    estado: Mapped[bool] = mapped_column(default=True)    # True = activa, False = cancelada

    ocurrencia: Mapped["Ocurrencia"] = relationship(back_populates="reservas")
