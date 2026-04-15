# CLAUDE.md

Este archivo proporciona contexto a Claude Code (claude.ai/code) para trabajar con el codigo de este repositorio.

## Que es esto

Sistema de reembolsos medicos de seguros de salud, construido como demo de vibe-coding en vivo para los dojos de desarrolladores de Tech&Solve. Simula el proceso colombiano de reembolsos regulado por la Superfinanciera (Decreto 2555/2010).

## Comandos

```bash
# Levantar el servidor de desarrollo (debe estar dentro de dojo-facturas/)
cd dojo-facturas && python -m uvicorn main:app --reload --port 8001

# Instalar dependencias
pip install -r dojo-facturas/requirements.txt

# Verificacion rapida de la logica de negocio
cd dojo-facturas && python -c "from database import init_db, seed_db; init_db(); seed_db(); print('OK')"
```

No hay tests automatizados, linter ni CI. La validacion se hace manualmente por la UI en `http://localhost:8001` y Swagger en `http://localhost:8001/docs`.

## Arquitectura

La app vive completamente en `dojo-facturas/`. Es una app FastAPI de pagina unica con frontend vanilla HTML/JS.

### Flujo de datos

```
static/index.html (frontend) → main.py (endpoints) → services.py (logica de negocio) → database.py (PostgreSQL)
```

- **models.py** — Modelos Pydantic con validadores. `SolicitudReembolso` es la entrada; `Reembolso` es la entidad persistida.
- **services.py** — Todas las reglas de negocio viven aqui. Tambien contiene `extraer_datos_factura()` que llama a Claude Vision API para extraer datos de imagenes de facturas.
- **database.py** — Conexiones psycopg2 directas (sin ORM). `init_db()` crea las tablas, `seed_db()` inserta 3 asegurados de prueba en la primera ejecucion. Ambas se ejecutan automaticamente al iniciar la app via `main.py @app.on_event("startup")`.
- **main.py** — Rutas FastAPI. Capa delgada que delega a services y mapea excepciones a errores HTTP.
- **static/index.html** — Un solo archivo HTML con CSS/JS embebido. Cuatro tabs: Radicar, Gestionar, Consultar, Asegurados.

### Maquina de estados

Las solicitudes de reembolso siguen una maquina de estados estricta definida en `services.py:TRANSICIONES`:

```
RADICADO → EN_REVISION_DOCUMENTAL → EN_AUDITORIA_MEDICA → EN_VALIDACION_COBERTURA → APROBADO → PAGADO
                ↓                         ↓                        ↓
          DEVUELTO_POR_DOCUMENTOS   RECHAZADO_MEDICO        RECHAZADO_COBERTURA
```

Los cambios de estado son validados — solo las transiciones permitidas tienen exito. Cada transicion se registra en `historial_estados`.

### Calculo del reembolso (al APROBAR)

Cuando un reembolso llega a APROBADO, `services.py:cambiar_estado()` calcula automaticamente:
1. Verifica que el tope_anual no se exceda
2. Aplica el deducible pendiente desde `asegurado.deducible_consumido`
3. Aplica el porcentaje de copago
4. Actualiza `deducible_consumido` y `reembolsado_anual` del asegurado

### Dependencias externas

- **PostgreSQL 16** en localhost:5432, base de datos `dojo_facturas_db`, usuario `app_admin`. La configuracion de conexion esta en `database.py` con soporte para variables de entorno.
- **API Claude Vision de Anthropic** para escaneo de imagenes de facturas. Requiere `ANTHROPIC_API_KEY` en `.env`. Usa `claude-sonnet-4-20250514`.

## Reglas de negocio clave (services.py)

- La poliza debe estar ACTIVA para radicar un reembolso
- La fecha de la factura no puede tener mas de 30 dias ni ser futura
- Los numeros de factura son unicos (no se permiten duplicados)
- El NIT debe tener 9-10 digitos
- Los rechazos (RECHAZADO_MEDICO, RECHAZADO_COBERTURA) requieren motivo obligatorio
- DELETE `/datos` reinicia reembolsos e historial pero conserva los asegurados (resetea sus contadores)
