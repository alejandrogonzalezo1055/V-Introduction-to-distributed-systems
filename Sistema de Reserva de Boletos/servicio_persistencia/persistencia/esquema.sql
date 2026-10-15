-- Una ocurrencia es una fecha concreta de un evento. Su cupo es independiente.
CREATE TABLE IF NOT EXISTS eventos (
    id_evento TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    tipo_evento TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ocurrencias (
    id_evento TEXT NOT NULL REFERENCES eventos(id_evento),
    numero INTEGER NOT NULL CHECK (numero > 0),
    fecha DATE NOT NULL,
    capacidad INTEGER NOT NULL CHECK (capacidad > 0),
    ocupados INTEGER NOT NULL DEFAULT 0 CHECK (ocupados >= 0 AND ocupados <= capacidad),
    PRIMARY KEY (id_evento, numero),
    UNIQUE (id_evento, fecha)
);

CREATE TABLE IF NOT EXISTS reservas (
    id_reserva BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente BIGINT NOT NULL CHECK (id_cliente > 0),
    id_evento TEXT NOT NULL,
    ocurrencia INTEGER NOT NULL,
    cantidad_asientos INTEGER NOT NULL CHECK (cantidad_asientos > 0),
    creada_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_evento, ocurrencia) REFERENCES ocurrencias(id_evento, numero)
);

CREATE INDEX IF NOT EXISTS ocurrencias_fecha_idx ON ocurrencias(fecha);
CREATE INDEX IF NOT EXISTS reservas_ocurrencia_idx ON reservas(id_evento, ocurrencia);
CREATE INDEX IF NOT EXISTS reservas_cliente_idx ON reservas(id_cliente);
