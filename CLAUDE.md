# CLAUDE.md

Este archivo proporciona contexto a Claude Code (claude.ai/code) para trabajar con el codigo de este repositorio.

## Que es esto

Sistema de reembolsos medicos de seguros de salud, construido como demo de vibe-coding en vivo para los dojos de desarrolladores de Tech&Solve. Simula el proceso colombiano de reembolsos regulado por la Superfinanciera (Decreto 2555/2010), Ley 1581/2012 (Habeas Data) y Ley 1751/2015.

## Comandos

```bash
# Levantar el servidor de desarrollo (debe estar dentro de dojo-facturas/)
cd dojo-facturas && python -m uvicorn main:app --reload --port 8001

# Instalar dependencias
pip install -r dojo-facturas/requirements.txt

# Generar facturas de ejemplo para probar escaneo
cd dojo-facturas && python generar_facturas.py

# Verificacion rapida de la logica de negocio
cd dojo-facturas && python -c "from database import init_db, seed_db; init_db(); seed_db(); print('OK')"
```

No hay tests automatizados, linter ni CI. La validacion se hace manualmente por la UI en `http://localhost:8001` y Swagger en `http://localhost:8001/docs`.

## Arquitectura

La app vive completamente en `dojo-facturas/`. Es una app FastAPI de pagina unica con frontend vanilla HTML/JS y navegacion por sidebar lateral.

### Flujo de datos

```
static/index.html (frontend con sidebar) → main.py (endpoints) → services.py (logica de negocio) → database.py (PostgreSQL)
```

- **models.py** — Modelos Pydantic con validadores. `SolicitudReembolso` es la entrada de reembolsos; `CrearAsegurado` y `EditarAsegurado` para el CRUD de asegurados; `CambioEstadoPoliza` para transiciones de poliza.
- **services.py** — Todas las reglas de negocio viven aqui. Contiene `extraer_datos_factura()` (Claude Vision API), CRUD de asegurados con maquina de estados de poliza, y flujo completo de reembolsos.
- **database.py** — Conexiones psycopg2 directas (sin ORM). `init_db()` crea las tablas y migra columnas nuevas con ALTER TABLE. `seed_db()` inserta 3 asegurados de prueba en la primera ejecucion. Ambas se ejecutan automaticamente al iniciar via `main.py @app.on_event("startup")`.
- **main.py** — Rutas FastAPI (15 endpoints). Capa delgada que delega a services y mapea excepciones a errores HTTP.
- **static/index.html** — Un solo archivo HTML con CSS/JS embebido. Sidebar lateral con 4 secciones: Radicar, Gestionar Reembolsos, Consultar, Gestionar Asegurados.
- **generar_facturas.py** — Script para generar 3 facturas medicas de ejemplo como imagenes PNG (usa Pillow). Las guarda en `facturas_ejemplo/`.

### Maquina de estados de reembolsos

Las solicitudes de reembolso siguen una maquina de estados estricta definida en `services.py:TRANSICIONES`:

```
RADICADO → EN_REVISION_DOCUMENTAL → EN_AUDITORIA_MEDICA → EN_VALIDACION_COBERTURA → APROBADO → PAGADO
                ↓                         ↓                        ↓
          DEVUELTO_POR_DOCUMENTOS   RECHAZADO_MEDICO        RECHAZADO_COBERTURA
```

Los cambios de estado son validados — solo las transiciones permitidas tienen exito. Cada transicion se registra en `historial_estados`.

### Maquina de estados de polizas

Las polizas de asegurados siguen su propia maquina definida en `services.py:TRANSICIONES_POLIZA`:

```
PENDIENTE_ACTIVACION → ACTIVA → SUSPENDIDA → ACTIVA (reactivacion)
           ↓               ↓           ↓
        CANCELADA       CANCELADA   CANCELADA
```

Suspender y cancelar requieren motivo obligatorio. No se puede cancelar si hay reembolsos en tramite. Reactivacion despues de 90 dias suspendida resetea contadores.

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

### Reembolsos
- La poliza debe estar ACTIVA para radicar un reembolso
- La fecha de la factura no puede tener mas de 30 dias ni ser futura
- Los numeros de factura son unicos (no se permiten duplicados)
- El NIT debe tener 9-10 digitos
- Los rechazos (RECHAZADO_MEDICO, RECHAZADO_COBERTURA) requieren motivo obligatorio
- Los datos de la factura son inmutables despues de radicados (no existe endpoint de edicion)
- Al escanear con IA, los campos auto-llenados se deshabilitan en el formulario
- DELETE `/datos` reinicia reembolsos e historial pero conserva los asegurados (resetea sus contadores)

### Asegurados (CRUD)
- Documento debe tener entre 6 y 12 caracteres, no duplicado
- Numero de poliza no duplicado
- Copago entre 0% y 30% (rango colombiano)
- No se puede bajar deducible_anual por debajo de deducible_consumido
- No se puede bajar tope_anual por debajo de reembolsado_anual
- Documento y tipo_documento no son editables despues de creacion
- No se puede eliminar asegurado con reembolsos asociados
