# Sistema de Reembolsos Medicos de Seguros

Sistema completo de reembolsos medicos de seguros de salud, construido como ejercicio de **vibe coding** en los dojos semanales de desarrolladores de [Tech&Solve](https://techandsolve.com).

Simula el proceso colombiano de reembolsos regulado por la Superintendencia Financiera (Decreto 2555/2010), con fuentes de HDI Seguros, SURA, Colmedica, Allianz y FASECOLDA.

> **Principio rector del dojo:** No complejizar. Empezar como un "hola mundo" y evolucionar paso a paso.

---

## Proceso de Negocio

El asegurado paga una consulta medica de su bolsillo, reune los documentos y solicita el reembolso a su aseguradora.

```mermaid
flowchart LR
    A["Asegurado paga\nconsulta medica"] --> B["Reune documentos\n(factura, historia clinica)"]
    B --> C["Radica solicitud\nen el sistema"]
    C --> D["Revision\ndocumental"]
    D --> E["Auditoria\nmedica"]
    E --> F["Validacion\nde cobertura"]
    F --> G["Aprobacion y\ncalculo de reembolso"]
    G --> H["Pago al\nasegurado"]

    D -->|Documentos incompletos| D2["Devuelto por\ndocumentos"]
    E -->|No pertinente| E2["Rechazado\nmedico"]
    F -->|Sin cobertura| F2["Rechazado\ncobertura"]

    style A fill:#e3f2fd
    style H fill:#c8e6c9
    style D2 fill:#fff3e0
    style E2 fill:#ffebee
    style F2 fill:#ffebee
```

---

## Maquina de Estados

Cada solicitud de reembolso sigue una maquina de estados estricta con transiciones validadas. Solo las transiciones permitidas tienen exito.

```mermaid
stateDiagram-v2
    [*] --> RADICADO
    RADICADO --> EN_REVISION_DOCUMENTAL

    EN_REVISION_DOCUMENTAL --> EN_AUDITORIA_MEDICA
    EN_REVISION_DOCUMENTAL --> DEVUELTO_POR_DOCUMENTOS

    DEVUELTO_POR_DOCUMENTOS --> RADICADO: Corrige y re-radica

    EN_AUDITORIA_MEDICA --> EN_VALIDACION_COBERTURA
    EN_AUDITORIA_MEDICA --> RECHAZADO_MEDICO

    EN_VALIDACION_COBERTURA --> APROBADO
    EN_VALIDACION_COBERTURA --> RECHAZADO_COBERTURA

    APROBADO --> PAGADO
    PAGADO --> [*]

    RECHAZADO_MEDICO --> [*]
    RECHAZADO_COBERTURA --> [*]
```

| Estado | Responsable | Descripcion |
|---|---|---|
| RADICADO | Sistema | Solicitud recibida |
| EN_REVISION_DOCUMENTAL | Gestor de reclamaciones | Verifica documentos completos |
| DEVUELTO_POR_DOCUMENTOS | Gestor | Faltan documentos o son ilegibles |
| EN_AUDITORIA_MEDICA | Medico auditor | Valida necesidad y pertinencia medica |
| RECHAZADO_MEDICO | Medico auditor | No es medicamente necesario |
| EN_VALIDACION_COBERTURA | Validador de cobertura | Verifica poliza, topes, exclusiones |
| RECHAZADO_COBERTURA | Validador | No cubierto o tope excedido |
| APROBADO | Sistema | Calcula valor a reembolsar |
| PAGADO | Sistema | Transferencia realizada |

---

## Arquitectura

```mermaid
flowchart TB
    subgraph Frontend
        HTML["static/index.html\n(HTML + CSS + JS vanilla)"]
    end

    subgraph Backend ["FastAPI Backend"]
        MAIN["main.py\n(11 endpoints)"]
        MODELS["models.py\n(Pydantic + validadores)"]
        SERVICES["services.py\n(logica de negocio)"]
        DB["database.py\n(PostgreSQL + seed)"]
    end

    subgraph External ["Servicios Externos"]
        PG[("PostgreSQL 16\ndojo_facturas_db")]
        CLAUDE["Claude Vision API\n(escaneo de facturas)"]
    end

    HTML -->|HTTP/JSON| MAIN
    MAIN --> MODELS
    MAIN --> SERVICES
    SERVICES --> DB
    SERVICES --> CLAUDE
    DB --> PG

    style Frontend fill:#e3f2fd
    style PG fill:#fff3e0
    style CLAUDE fill:#f3e5f5
```

---

## Modelo de Datos

```mermaid
erDiagram
    ASEGURADOS {
        serial id PK
        varchar documento UK "Cedula"
        varchar nombre
        varchar numero_poliza
        varchar plan "Basico, Plus, Premium"
        varchar estado_poliza "ACTIVA, SUSPENDIDA, CANCELADA"
        numeric deducible_anual
        numeric deducible_consumido
        numeric tope_anual
        numeric reembolsado_anual
        integer copago_porcentaje
    }

    REEMBOLSOS {
        varchar id PK "UUID"
        varchar numero_factura UK
        varchar documento_asegurado FK
        varchar nit_prestador
        varchar nombre_prestador
        varchar tipo_servicio "CONSULTA, LABORATORIO, etc."
        varchar diagnostico_codigo "CIE-10"
        varchar diagnostico_descripcion
        date fecha_servicio
        timestamp fecha_radicacion
        numeric valor_factura
        numeric valor_aprobado
        varchar estado "9 estados posibles"
        text motivo_rechazo
        text observaciones
    }

    HISTORIAL_ESTADOS {
        serial id PK
        varchar reembolso_id FK
        varchar estado_anterior
        varchar estado_nuevo
        varchar responsable
        timestamp fecha
        text observacion
    }

    ASEGURADOS ||--o{ REEMBOLSOS : "solicita"
    REEMBOLSOS ||--o{ HISTORIAL_ESTADOS : "registra cambios"
```

---

## Calculo del Reembolso

Cuando un reembolso llega al estado **APROBADO**, el sistema calcula automaticamente:

```
1. Verificar tope anual: reembolsado_anual + valor_factura <= tope_anual
2. Deducible pendiente = deducible_anual - deducible_consumido
3. Valor despues de deducible = valor_factura - deducible_pendiente (minimo 0)
4. Valor aprobado = valor_despues_deducible * (1 - copago%)
```

**Ejemplo:** Factura de $2.000.000, deducible pendiente $320.000, copago 20%:
```
Despues de deducible: $2.000.000 - $320.000 = $1.680.000
Valor aprobado: $1.680.000 * 0.80 = $1.344.000
```

---

## Reglas de Negocio

| # | Regla | Momento |
|---|---|---|
| 1 | Poliza del asegurado debe estar ACTIVA | Al radicar |
| 2 | Factura no puede tener mas de 30 dias desde el servicio | Al radicar |
| 3 | Fecha del servicio no puede ser futura | Al radicar |
| 4 | Numero de factura no puede estar duplicado | Al radicar |
| 5 | NIT del prestador debe tener 9-10 digitos | Al radicar |
| 6 | Tipo de servicio debe ser valido (CONSULTA, LABORATORIO, MEDICAMENTOS, HOSPITALIZACION, CIRUGIA) | Al radicar |
| 7 | Valor de factura debe ser mayor a cero | Al radicar |
| 8 | Transiciones de estado solo las permitidas | Al cambiar estado |
| 9 | Rechazos (medico/cobertura) requieren motivo obligatorio | Al rechazar |
| 10 | Tope anual no puede ser excedido | Al aprobar |
| 11 | Deducible y copago se aplican automaticamente | Al aprobar |

---

## Endpoints API

| Metodo | Ruta | Descripcion |
|---|---|---|
| `GET` | `/` | Sirve el frontend |
| `GET` | `/asegurados` | Lista todos los asegurados |
| `GET` | `/asegurados/{documento}` | Consulta un asegurado por cedula |
| `POST` | `/facturas/escanear` | Extrae datos de imagen con Claude Vision |
| `POST` | `/reembolsos` | Radica solicitud de reembolso |
| `GET` | `/reembolsos` | Lista reembolsos (filtro opcional `?estado=`) |
| `GET` | `/reembolsos/{numero_factura}` | Consulta reembolso por numero de factura |
| `PATCH` | `/reembolsos/{id}/estado` | Cambia estado de un reembolso |
| `GET` | `/reembolsos/{id}/historial` | Historial de estados de un reembolso |
| `DELETE` | `/datos` | Reinicia reembolsos (conserva asegurados) |

Swagger UI disponible en `/docs`.

---

## Estructura del Proyecto

```
dojo-facturas/
├── .env                 # ANTHROPIC_API_KEY (no subir al repo)
├── database.py          # Conexion PostgreSQL + init_db + seed
├── main.py              # App FastAPI — 11 endpoints
├── models.py            # Modelos Pydantic con validadores
├── services.py          # Logica de negocio + reglas + Claude Vision
├── requirements.txt     # Dependencias Python
└── static/
    └── index.html       # Frontend completo con 4 tabs

context/
├── Dojo.txt             # Transcripcion original de la planeacion
└── historial-desarrollo.md  # 14 pasos progresivos del desarrollo

CLAUDE.md                # Contexto para Claude Code
README.md                # Este archivo
```

---

## Datos de Prueba

El sistema crea automaticamente 3 asegurados al iniciar:

| Nombre | Documento | Plan | Poliza | Deducible | Tope Anual | Copago |
|---|---|---|---|---|---|---|
| Maria Lopez | 1017234567 | Premium | ACTIVA | $500.000 | $50.000.000 | 20% |
| Carlos Ruiz | 1098765432 | Basico | ACTIVA | $1.000.000 | $20.000.000 | 30% |
| Ana Garcia | 1045678901 | Plus | SUSPENDIDA | $750.000 | $35.000.000 | 25% |

Ana Garcia tiene poliza SUSPENDIDA para probar el rechazo al radicar.

---

## Requisitos

- Python 3.10+
- PostgreSQL 16
- API key de Anthropic (para escaneo de facturas con IA)

## Instalacion y Ejecucion

```bash
# 1. Clonar el repositorio
git clone https://github.com/gabocolo/dojo-reembolsos.git
cd dojo-reembolsos

# 2. Instalar dependencias
pip install -r dojo-facturas/requirements.txt

# 3. Crear la base de datos en PostgreSQL
createdb dojo_facturas_db

# 4. Configurar variables de entorno
cp dojo-facturas/.env.example dojo-facturas/.env
# Editar .env con tu ANTHROPIC_API_KEY y credenciales de PostgreSQL

# 5. Levantar el servidor
cd dojo-facturas
python -m uvicorn main:app --reload --port 8001

# 6. Abrir en el navegador
# http://localhost:8001
```

Las tablas y datos de prueba se crean automaticamente al iniciar el servidor.

### Variables de Entorno

| Variable | Default | Descripcion |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | API key de Anthropic (requerida para escaneo) |
| `PG_HOST` | `localhost` | Host de PostgreSQL |
| `PG_PORT` | `5432` | Puerto de PostgreSQL |
| `PG_DATABASE` | `dojo_facturas_db` | Nombre de la base de datos |
| `PG_USER` | `app_admin` | Usuario de PostgreSQL |
| `PG_PASSWORD` | `dev_password_change_me` | Password de PostgreSQL |

---

## Contexto: Dojo de Vibe Coding

Este proyecto se construyo en vivo durante los dojos semanales de **Tech&Solve**, donde lideres tecnicos de desarrollo aprenden a construir software con IA (vibe coding).

**Formato:** Viernes 4:00 PM - 5:30 PM | Solo desarrolladores y lideres tecnicos

El sistema evoluciono progresivamente en 14 pasos documentados en [`context/historial-desarrollo.md`](context/historial-desarrollo.md) — desde un "hola mundo" con FastAPI hasta un sistema completo de reembolsos medicos con maquina de estados, escaneo por IA y base de datos PostgreSQL.

### Stack Tecnologico

| Tecnologia | Uso |
|---|---|
| Python + FastAPI | Backend API |
| Pydantic | Validacion de datos |
| PostgreSQL 16 + psycopg2 | Persistencia |
| Claude Vision API | Escaneo de facturas por imagen |
| HTML + CSS + JS vanilla | Frontend (single page) |
| GitHub CLI | Gestion del repositorio |

---

*Construido con vibe coding usando [Claude Code](https://claude.ai/code)*
