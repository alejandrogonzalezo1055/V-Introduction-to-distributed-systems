# Sistema de Reserva de Boletos (SRB)

Proyecto de **Introducción a los Sistemas Distribuidos** (periodo 2026-30) — Departamento de Ingeniería de Sistemas, Pontificia Universidad Javeriana.

Sistema distribuido basado en servicios para reservar boletos de eventos culturales y deportivos de una universidad. Permite **consultar** eventos de un mes, **reservar** puestos, **modificar** una reserva (de forma síncrona) y **cancelar** una reserva (de forma asíncrona, con notificación posterior al cliente). La comunicación entre procesos se hace con [ZeroMQ](https://zeromq.org/) (`pyzmq`).

**Autores:** Solon Losada Cadena · Juan Pablo Peña Bernal · Alejandro González Ochoa
**Docente:** Ricardo Hjalmar González García

---

## Arquitectura

Estilo arquitectónico de **tres capas**, cada una pensada para desplegarse en una máquina distinta:

| Capa | Procesos | Responsabilidad |
|------|----------|-----------------|
| **Consumidores** | Clientes (`Cliente`, generador de carga) | Envían consulta, reserva, modificación y cancelación; reciben notificaciones de cancelación. |
| **Servicios de negocio** | Gestor de Transacciones (GT), servicio RMC, servicio de Cancelación y Notificación | El GT enruta por el canal síncrono o asíncrono; RMC atiende reservas, modificaciones y consultas; Cancelación procesa las cancelaciones y notifica. |
| **Persistencia** | Servicio de persistencia + PostgreSQL | Único componente con acceso a la base de datos (operaciones CRUD con SQLAlchemy). |

### Patrones de comunicación (ZeroMQ)

- **Síncrono** — `REQ` (cliente) ⇄ `ROUTER` (GT) ⇄ `DEALER` ⇄ `REP` (RMC). El `ROUTER/DEALER` permite varias solicitudes simultáneas y cada petición lleva un `uuid` único.
- **Asíncrono** — `PUSH/PULL` (pipeline) entre el GT y el servicio de cancelación, con balanceo round-robin para escalar. El cliente recibe una aceptación inmediata y, cuando la cancelación se hace efectiva en la base de datos, una notificación en su socket `PULL`.
- **RMC → Persistencia** — `REQ/REP`.

### Flujo de una petición síncrona

```
Cliente (REQ) ──► GT (ROUTER) ──► GT (DEALER) ──► RMC (REP) ──► Persistencia ──► PostgreSQL
      ◄──────────────────────────────── respuesta ◄──────────────────────────────
```

Para **reservar**, el RMC primero pide la disponibilidad (`CONSULTA_DISPONIBILIDAD`) y, si hay cupo suficiente, solicita a persistencia `AGREGAR_RESERVA`.

### Modelos del sistema

El informe documenta los modelos de interacción (síncrono/asíncrono), de fallos (*fail-stop* en GT y RMC, detección por *timeouts* y señales de vida) y de seguridad (los mensajes ZeroMQ viajan en texto plano si el canal no se asegura; riesgo de DoS sobre el GT). También describe la estrategia de escalabilidad horizontal (contenedores por proceso, replicación de PostgreSQL) y el protocolo de pruebas (unitarias, integración, concurrencia, fallos, seguridad, rendimiento con Locust con 3, 5 y 8 clientes, estrés y regresión).

---

## Estructura del repositorio

```
.
├── EnunciadoProyecto_sdp_Reserva de boletas.pdf   # Enunciado del proyecto
├── Informe proyecto/
│   ├── Informe Proyecto.tex / .pdf                # Informe (LaTeX) con modelos, diseño y plan de pruebas
│   └── Images/                                    # Diagramas: capas, componentes, despliegue, clases, secuencia
├── Guias/
│   ├── SQLAlchemy para Persistencia.html          # Guía para implementar la capa de persistencia
│   └── SRB — Guía rápida del código (primera entrega).pdf
├── Sistema de Reserva de Boletos/                 # Código fuente del sistema
│   ├── requirements.txt
│   ├── comun/
│   │   ├── .env                                   # Hosts y puertos de cada capa
│   │   ├── config.py                              # Carga del .env y utilidades de sockets
│   │   └── mensajes.py                            # Formato de peticiones/respuestas (JSON)
│   ├── capa_consumidores/
│   │   ├── cliente.py                             # Clase Cliente (REQ hacia el GT)
│   │   ├── carga_clientes.py                      # Generador de carga parametrizable
│   │   └── consumers_main.py                      # Punto de entrada de la capa
│   ├── capa_servicios/
│   │   ├── service_main.py                        # Punto de entrada: arranca `gt` o `rmc`
│   │   ├── gestor_transacciones/                  # GT (ROUTER/DEALER)
│   │   ├── servicio_RMC/                          # Reservas, Modificaciones y Consultas
│   │   └── cancelacion_y_notificacion/            # Cancelación asíncrona (PUSH/PULL)
│   └── capa_persistencia/
│       └── persistence_main.py                    # Punto de entrada de persistencia
├── ZeroMQ examples/                               # Ejemplos de referencia (req/rep, pub/sub, push/pull)
└── .github/workflows/latex.yml                    # CI: compila el informe LaTeX en ramas `features-*`
```

---

## Protocolo de mensajes

Los mensajes son JSON (`comun/mensajes.py`).

**Petición**

```json
{ "uuid": "…", "tipo": "RESERVA", "id_cliente": 1, "datos": { "id_evento": "E1", "fecha": "2026/10/20", "n_asientos": 5 } }
```

**Respuesta**

```json
{ "uuid": "…", "estado": "EXITO", "motivo": "…", "datos": { } }
```

| Campo | Valores |
|-------|---------|
| `tipo` | `CONSULTA`, `CONSULTA_DISPONIBILIDAD`, `RESERVA`, `AGREGAR_RESERVA`, `MODIFICACION`, `CANCELACION`, `NOTIFICACION` |
| `estado` | `EXITO`, `FALLO`, `ERROR`, `ACK` |
| `motivo` | `SIN_CUPO`, `NO_EXISTE`, `DATO_INVALIDO`, `PETICION_INVALIDA`, `NO_IMPLEMENTADO` |

---

## Puesta en marcha

### Requisitos

- Python 3.10+ (el entorno de desarrollo usa 3.14)
- PostgreSQL (para la capa de persistencia)

### Instalación

```bash
cd "Sistema de Reserva de Boletos"
python -m venv .venv
source .venv/bin/activate        # En fish: source .venv/bin/activate.fish
pip install -r requirements.txt   # pyzmq, python-dotenv, sqlalchemy, psycopg[binary]
```

### Configuración

Edite `comun/.env` con las IP de las máquinas donde correrá cada capa y los puertos:

```ini
HOST_CAPA_CONSUMIDORES=<ip>
HOST_CAPA_SERVICIOS=<ip>
HOST_CAPA_PERSISTENCIA=<ip>

GT_PUERTO_CLIENTES=5555     # clientes  -> GT
GT_PUERTO_RMC=5556          # GT        -> RMC
GT_PUERTO_CANCELACION=5557  # GT        -> cancelación

PUERTO_SP=5558              # servicio de persistencia
DB_URL=…
DB_PASSWD=…
```

> No suba credenciales reales de la base de datos al repositorio.

### Ejecución

Todos los comandos se ejecutan desde la carpeta `Sistema de Reserva de Boletos/`.

```bash
# Máquina de servicios
python -m capa_servicios.service_main gt     # Gestor de Transacciones
python -m capa_servicios.service_main rmc    # Servicio RMC

# Máquina de consumidores
python -m capa_consumidores.carga_clientes   # Generador de carga (cliente con id 1)
```

Parámetros del generador de carga (`carga_clientes.py`): solicitudes por minuto (`sol_minuto`), porcentaje de consultas frente a reservas (`porcen_cons`) y duración en minutos.

---

## Estado actual del desarrollo

| Componente | Estado |
|------------|--------|
| Cliente (consulta y reserva) y generador de carga | Implementado |
| Mensajes y configuración comunes | Implementado |
| Gestor de Transacciones (canal síncrono ROUTER/DEALER) | Implementado |
| Servicio RMC: consulta y reserva | Implementado |
| Servicio RMC: modificación | Pendiente (responde `NO_IMPLEMENTADO`) |
| Cancelación asíncrona y notificaciones (PUSH/PULL) | Pendiente (clase vacía) |
| Capa de persistencia (SQLAlchemy + PostgreSQL) | En desarrollo (solo archivo base; ver guía en `Guias/`) |
| Tolerancia a fallos (timeouts, señales de vida, réplicas) | Diseñado en el informe, sin implementar |
| Pruebas de rendimiento con Locust | Planeado |

### Problemas conocidos

- `service_main.py` no llama a `iniciar_poller()` antes de `iniciar_gestor()` en el GT.
- `Servicio_RMC.crear_reserva` aplica `decodificar` a una petición que ya llega decodificada.
- `carga_clientes.py` ejecuta `main_carga()` al importarse (sin guardia `if __name__ == "__main__"`).
- `consumers_main.py` es un esqueleto y el mensaje de uso de `service_main.py` menciona `capa_servicios.main`.

---

## Documentación

- **Enunciado:** `EnunciadoProyecto_sdp_Reserva de boletas.pdf`
- **Informe:** `Informe proyecto/Informe Proyecto.pdf` (se recompila automáticamente con GitHub Actions al hacer push a ramas `features-*`)
- **Guías:** `Guias/`
- **Ejemplos ZeroMQ:** `ZeroMQ examples/`

## Flujo de trabajo

Rama principal: `main`. El desarrollo se hace en ramas `features-<nombre>` y se integra mediante Pull Request.
