# Historial de Desarrollo — Sistema de Desembolsos por Factura

## Origen

Conversación entre **Juan Gabriel Colorado** y **Andrés Felipe Muñeton Lopera** (transcripción en `Dojo.txt`) para planificar un dojo semanal de **vibe coding** dirigido a líderes técnicos de desarrollo en Tech&Solve.

### Objetivo del dojo
Demostrar en vivo cómo se construye software con IA — el público debe ver que se escribe una instrucción y se genera código funcional, evolucionando progresivamente.

### Principio rector
**No complejizar.** Empezar como un "hola mundo" y evolucionar paso a paso. Evitar debates de arquitectura.

### Formato
- Viernes 4:00 PM - 5:30 PM (objetivo: 1 hora)
- Audiencia: solo desarrolladores / líderes técnicos
- Compartir el código al final
- Recurrencia: dojos semanales

---

## Decisiones técnicas

| Decisión | Elección | Razón |
|---|---|---|
| Stack | Python + FastAPI | Rápido de prototipar, visual en demos |
| Formato factura | JSON simple (+ escaneo por imagen) | Foco en vibe coding |
| Desembolso | Mock/simulado | Sin dependencias externas |
| Validaciones | Básicas (NIT, valor, factura) | Claras y progresivas |
| OCR/Extracción | Claude Vision API | On-brand con el tema de IA |

---

## Evolución del producto — Paso a paso

### Paso 1: Hola Mundo
**Prompt:** "Crea un proyecto Python con FastAPI que tenga un endpoint POST /facturas que reciba un JSON con número de factura, NIT del cliente, nombre del cliente y valor total, y devuelva un mensaje de confirmación"

**Resultado:**
- `main.py` con endpoint POST `/facturas`
- `models.py` con modelo Pydantic `Factura`
- `requirements.txt` con fastapi, uvicorn, pydantic
- Response simple: "Factura recibida"

**Archivos creados:** `main.py`, `models.py`, `requirements.txt`

---

### Paso 2: Validaciones
**Prompt:** "Agrega validaciones: el NIT debe tener entre 9 y 10 dígitos, el valor total debe ser mayor a cero, y el número de factura no puede estar vacío. Devuelve errores claros si algo falla"

**Resultado:**
- `field_validator` en modelo Pydantic para NIT (9-10 dígitos), valor (>0), factura (no vacía)
- HTTP 422 automático con mensajes descriptivos

**Archivos modificados:** `models.py`

---

### Paso 3: Lógica de desembolso
**Prompt:** "Agrega un servicio que procese el desembolso: debe generar un ID único de transacción, registrar la fecha, y simular que el pago fue exitoso. El endpoint debe devolver los datos del desembolso con el ID de transacción y el estado"

**Resultado:**
- `services.py` con función `procesar_desembolso()`
- UUID para ID de transacción
- Modelo `Desembolso` con transaction_id, estado, fecha, mensaje
- Almacenamiento en memoria (diccionario `desembolsos_db`)

**Archivos creados:** `services.py`
**Archivos modificados:** `models.py`, `main.py`

---

### Paso 4: Regla de negocio (límite de desembolso)
**Prompt:** "Simula que si el valor de la factura supera 10.000.000, el desembolso es rechazado por superar el límite diario. Devuelve un error apropiado con el motivo del rechazo"

**Resultado:**
- Constante `LIMITE_DIARIO = 10_000_000` en services.py
- HTTP 400 con mensaje: "Desembolso rechazado: el valor $X supera el límite diario de $10,000,000"

**Archivos modificados:** `services.py`

---

### Paso 5: Consultar estado de desembolso
**Prompt:** "Agrega un endpoint GET /desembolsos/{transaction_id} para consultar el estado de un desembolso"

**Resultado:**
- Endpoint GET `/desembolsos/{transaction_id}`
- HTTP 404 si no existe

**Archivos modificados:** `main.py`

---

### Paso 6: Frontend
**Prompt:** "Crea un frontend para ver el escenario"

**Resultado:**
- `static/index.html` — interfaz web completa
- Panel izquierdo: formulario para registrar factura
- Panel derecho: consultar desembolso por ID
- Swagger UI disponible en `/docs`
- FastAPI sirve archivos estáticos desde `/static`

**Archivos creados:** `static/index.html`
**Archivos modificados:** `main.py` (mount static files, FileResponse para `/`)

---

### Paso 7: Flujo de aprobación/rechazo
**Prompt:** "Debemos tener la opción para rechazar o aprobar el desembolso"

**Cambio de flujo:**
- Antes: factura → desembolso APROBADO automáticamente
- Ahora: factura → desembolso PENDIENTE → humano aprueba o rechaza

**Resultado:**
- Modelo `Decision` (accion: APROBAR/RECHAZAR, motivo opcional)
- Función `decidir_desembolso()` en services.py
- Función `listar_pendientes()` en services.py
- Endpoint PATCH `/desembolsos/{transaction_id}` para aprobar/rechazar
- Endpoint GET `/desembolsos/pendientes` para listar pendientes
- Frontend: bandeja de aprobaciones con tabla de pendientes
- Modal de confirmación con campo de motivo opcional
- Badges de estado: amarillo (PENDIENTE), verde (APROBADO), rojo (RECHAZADO)

**Archivos modificados:** `models.py`, `services.py`, `main.py`, `static/index.html`

---

### Paso 8: Escaneo de factura con IA (Claude Vision)
**Prompt:** "Adicionarle que debe cargar los datos de la factura desde una imagen"

**Resultado:**
- Función `extraer_datos_factura()` en services.py — envía imagen a Claude Vision API
- Modelo: `claude-sonnet-4-20250514`
- Prompt estructurado pidiendo JSON con los 4 campos de factura
- Endpoint POST `/facturas/escanear` — recibe UploadFile, retorna datos extraídos
- Frontend: zona de drop/click para subir imagen con preview
- Auto-llena los campos del formulario tras el escaneo
- El usuario revisa y confirma antes de enviar
- Dependencias nuevas: `anthropic`, `python-dotenv`, `python-multipart`
- Requiere `ANTHROPIC_API_KEY` en archivo `.env`

**Archivos modificados:** `requirements.txt`, `services.py`, `main.py`, `static/index.html`
**Archivos creados:** `.env`

---

### Paso 9: Botón de reiniciar datos
**Prompt:** "Creame un botón de reiniciar datos"

**Resultado:**
- Función `reiniciar_datos()` en services.py
- Endpoint DELETE `/datos`
- Botón rojo en el header del frontend con confirmación
- Limpia todos los desembolsos en memoria/BD

**Archivos modificados:** `services.py`, `main.py`, `static/index.html`

---

### Paso 10: Limpiar imagen y formulario
**Prompt:** "Agrega eliminar imagen si está cargada, y formulario de factura"

**Resultado:**
- Botón "Limpiar imagen y formulario" que aparece solo cuando hay imagen cargada
- Limpia: preview de imagen, campos del formulario, estado del escaneo

**Archivos modificados:** `static/index.html`

---

### Paso 11: Migración a PostgreSQL
**Prompt:** "Migre el almacenamiento en memoria del proyecto a esta base de datos"

**Resultado:**
- Base de datos `dojo_facturas_db` creada en PostgreSQL local
- `database.py` con conexión a PostgreSQL
- Todas las funciones de services.py migradas de diccionario a queries SQL
- Los datos ahora persisten entre reinicios del servidor
- Dependencia nueva: `psycopg2-binary`

**Archivos creados:** `database.py`
**Archivos modificados:** `services.py`, `requirements.txt`

---

### Paso 12: Sección de facturas enviadas + validación de duplicados + consulta por número de factura
**Prompts:**
- "Creame una sección para consultar las facturas enviadas"
- "Debes validar el consecutivo de la factura para que no se tengan repetidos"
- "Consultar desembolso debe ser con Número de Factura"

**Resultado:**
- Endpoint GET `/desembolsos` para listar todos los desembolsos
- Sección "Facturas Enviadas" con tabla (factura, cliente, valor, estado, fecha)
- Al hacer clic en una fila copia el número de factura al campo de consulta
- Validación de factura duplicada al registrar
- Consulta de desembolso cambiada de transaction_id a número de factura

**Archivos modificados:** `services.py`, `main.py`, `static/index.html`

---

### Paso 13: Evolución a Sistema de Reembolsos Médicos de Seguros
**Prompt:** "Ayúdame a entender cómo sería este sistema en el ambiente de los seguros donde un cliente va a una consulta médica particular y con la factura podría venir a solicitar un reembolso"

**Investigación:** Se investigaron fuentes verificadas (HDI Seguros, SURA, Colmédica, Allianz, FASECOLDA, Superfinanciera, Decreto 2555/2010) para entender el proceso real de reembolsos médicos en Colombia.

**Resultado — Rediseño completo del sistema:**

**Modelo de datos:**
- Tabla `asegurados` — datos del cliente con póliza, plan, deducible, tope anual, copago
- Tabla `reembolsos` — solicitud completa con prestador, tipo de servicio, diagnóstico CIE-10, máquina de estados
- Tabla `historial_estados` — auditoría de cada cambio de estado con responsable y fecha

**Máquina de 9 estados:**
```
RADICADO → EN_REVISION_DOCUMENTAL → EN_AUDITORIA_MEDICA → EN_VALIDACION_COBERTURA → APROBADO → PAGADO
                ↓                         ↓                        ↓
          DEVUELTO_POR_DOCUMENTOS   RECHAZADO_MEDICO        RECHAZADO_COBERTURA
```

**Reglas de negocio implementadas:**
1. Póliza del asegurado debe estar ACTIVA
2. Plazo máximo de 30 días desde la fecha del servicio
3. Factura no duplicada
4. NIT del prestador válido (9-10 dígitos)
5. Tipo de servicio válido (CONSULTA, LABORATORIO, MEDICAMENTOS, HOSPITALIZACION, CIRUGIA)
6. Transiciones de estado validadas (solo las permitidas)
7. Rechazos requieren motivo obligatorio
8. Tope anual no excedido al aprobar
9. Cálculo automático del reembolso: valor_factura - deducible_pendiente, luego copago %
10. Actualización de deducible consumido y reembolsado anual del asegurado

**Frontend rediseñado con 4 tabs:**
- **Radicar** — formulario completo + escaneo IA + lista de asegurados (clic para auto-llenar documento)
- **Gestionar** — bandeja filtrable por estado con botones de transición y modal de cambio
- **Consultar** — búsqueda por número de factura + timeline visual del historial de estados
- **Asegurados** — tabla con detalle de póliza, deducibles y topes

**Datos de prueba (seed automático al iniciar):**
- María López — Plan Premium, póliza ACTIVA, copago 20%
- Carlos Ruiz — Plan Básico, póliza ACTIVA, copago 30%
- Ana García — Plan Plus, póliza SUSPENDIDA (para probar rechazo)

**Archivos modificados:** `database.py`, `models.py`, `services.py`, `main.py`, `static/index.html`

---

### Paso 14: Repositorio en GitHub
**Prompt:** "Vamos a conectarnos a un repositorio de github"

**Resultado:**
- Instalación de GitHub CLI (`gh` v2.89.0) via `winget`
- Autenticación con `gh auth login` en cuenta `gabocolo`
- Inicialización de git en el directorio raíz `Dojo/`
- `.gitignore` creado (excluye `.env`, `__pycache__`, `.mcp.json`, IDEs)
- Commit inicial con 10 archivos (código, frontend, contexto, documentación)
- Repositorio público creado: **https://github.com/gabocolo/dojo-reembolsos**
- Push automático con `gh repo create --source=. --push`

**Archivos creados:** `.gitignore`
**Comando clave:** `gh repo create gabocolo/dojo-reembolsos --public --source=. --remote=origin --push`

---

### Paso 15: README.md con diagramas
**Prompt:** "Créame el archivo README.MD con toda la información del proyecto, diagramas mermaid que consideres necesarios"

**Resultado:**
- `README.md` completo con documentación del proyecto
- 4 diagramas Mermaid: proceso de negocio, máquina de estados, arquitectura, modelo de datos (ER)
- Secciones: cálculo del reembolso, reglas de negocio, endpoints API, estructura, datos de prueba, instalación
- Contexto del dojo de vibe coding de Tech&Solve

**Archivos creados:** `README.md`

---

### Paso 16: Mejora visual de tabs y filtros de bandeja
**Prompt:** "En la Bandeja de Gestión no se distingue bien en qué pestaña se encuentra el usuario, dale más claridad"

**Resultado:**
- Tab activo con borde inferior azul (#4361ee), fondo blanco y sombra — mayor contraste visual
- Tabs inactivos transparentes con hover suave
- Barra de tabs con fondo gris (#e2e4e8) que da contraste
- Filtros de la bandeja de gestión ahora marcan cuál está seleccionado (fondo oscuro + borde azul)
- Se agregó filtro "Pagados" que faltaba

**Archivos modificados:** `static/index.html`

---

### Paso 17: CRUD de Asegurados con normativa colombiana
**Prompt:** "Vamos a hacer el CRUD del asegurado, investiga en internet reglas, normativas para la gestión de asegurados"

**Investigación:** Se investigaron normativas colombianas aplicables:
- **Decreto 2555/2010** — Ciclo de vida de pólizas, períodos de carencia, reglas de retracto (10 días libres tras activación)
- **Ley 1581/2012 (Habeas Data)** — Protección de datos personales, datos de salud son "sensibles", requiere consentimiento
- **Circular Básica Jurídica Superfinanciera** — Transiciones de estado de póliza, plazos de respuesta, mora y suspensión
- **Ley 1751/2015 (Estatutaria de Salud)** — Preexistencias cubiertas después de períodos de carencia

**Resultado — CRUD completo con reglas de negocio:**

**Nuevos campos del modelo `asegurados`:**
| Campo | Tipo | Descripción |
|---|---|---|
| tipo_documento | VARCHAR(5) | CC, CE, TI, PP, NIT |
| fecha_nacimiento | DATE | Edad del asegurado |
| genero | VARCHAR(10) | F, M, O |
| email | VARCHAR(200) | Contacto para notificaciones |
| telefono | VARCHAR(20) | Contacto telefónico |
| fecha_inicio_poliza | DATE | Inicio de vigencia |
| fecha_fin_poliza | DATE | Fin de vigencia |
| fecha_suspension | DATE | Cuándo fue suspendida |
| periodo_carencia_dias | INTEGER | Días de espera antes de cobertura (default 30) |
| preexistencias | TEXT | Condiciones preexistentes declaradas |
| motivo_estado | TEXT | Razón del estado actual de la póliza |

**Máquina de estados de póliza:**
```
PENDIENTE_ACTIVACION → ACTIVA → SUSPENDIDA → ACTIVA (reactivación)
           ↓               ↓           ↓
        CANCELADA       CANCELADA   CANCELADA
```

**Reglas de negocio implementadas:**
1. Documento debe tener entre 6 y 12 caracteres, no duplicado
2. Número de póliza no duplicado
3. Copago validado entre 0% y 30% (rango colombiano)
4. Estado inicial: ACTIVA si fecha_inicio <= hoy, sino PENDIENTE_ACTIVACION
5. Suspender y cancelar requieren motivo obligatorio
6. No se puede cancelar póliza si hay reembolsos en trámite (RADICADO, EN_REVISION, etc.)
7. Reactivación después de 90 días suspendida resetea contadores (deducible y reembolsado)
8. No se puede eliminar asegurado con reembolsos asociados
9. No se puede bajar deducible_anual por debajo de deducible_consumido
10. No se puede bajar tope_anual por debajo de reembolsado_anual
11. Documento y tipo_documento no editables después de creación

**Nuevos endpoints:**
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/asegurados` | Crear asegurado |
| PUT | `/asegurados/{documento}` | Editar asegurado |
| PATCH | `/asegurados/{documento}/estado` | Cambiar estado de póliza |
| DELETE | `/asegurados/{documento}` | Eliminar asegurado |

**Frontend — Tab Asegurados rediseñado:**
- Panel izquierdo: formulario de crear/editar con campos agrupados (datos personales, póliza, financieros)
- Panel derecho: tabla de asegurados con badges de estado de póliza y botones de acción
- Acciones en tabla: Editar, Activar/Suspender/Cancelar (según transiciones permitidas), Eliminar (solo canceladas)
- Modal de edición: pre-llena campos, deshabilita documento y póliza (no editables)
- Prompts para motivo al suspender o cancelar

**Migración de base de datos:**
- `init_db()` ahora agrega columnas nuevas con `ALTER TABLE ADD COLUMN` si la tabla ya existía
- Cada ALTER es una transacción independiente (commit/rollback) para no romper tablas existentes
- Seed actualizado con datos completos (fechas de nacimiento, emails, teléfonos, fecha de póliza)

**Archivos modificados:** `models.py`, `database.py`, `services.py`, `main.py`, `static/index.html`

---

### Paso 18: Navegación con sidebar lateral
**Prompt:** "Vamos a separar en un menú lateral para que quede la opción para radicar un documento, y otra opción para Gestionar el asegurado y sacarlo de los tabs de Radicar documento"

**Resultado:**
- Se reemplazó el layout de tabs superiores por un **sidebar lateral fijo** (240px) con fondo oscuro
- Sidebar organizado en 2 secciones:
  - **Reembolsos**: Radicar, Gestionar, Consultar
  - **Asegurados**: Gestionar
- Item activo con borde azul lateral (`border-left: 3px solid #4361ee`) y fondo destacado
- Botón "Reiniciar datos" movido al footer del sidebar
- Se eliminó el header superior — el título y subtítulo viven en el sidebar
- Cada sección es una página independiente (ya no son tabs con barra superior)
- La lista de asegurados en "Radicar" se mantiene como referencia rápida para copiar el documento
- El CRUD de asegurados vive separado en su propia sección "Gestionar Asegurados"
- Responsive: en pantallas < 900px el sidebar se colapsa a iconos (56px)

**Archivos modificados:** `static/index.html`

---

## Estructura final del proyecto

```
Dojo/
├── .gitignore               # Excluye .env, __pycache__, .mcp.json
├── CLAUDE.md                # Contexto para Claude Code
├── README.md                # Documentación completa con diagramas Mermaid
├── context/
│   ├── Dojo.txt             # Transcripción original de la planeación
│   └── historial-desarrollo.md  # Este archivo — pasos progresivos del dojo
└── dojo-facturas/
    ├── .env                 # ANTHROPIC_API_KEY (no subir al repo)
    ├── .mcp.json            # Config MCP para PostgreSQL
    ├── database.py          # Conexión PostgreSQL + init_db + seed
    ├── main.py              # App FastAPI — 15 endpoints
    ├── models.py            # Modelos Pydantic con validadores
    ├── services.py          # Lógica de negocio + reglas + Claude Vision
    ├── requirements.txt     # Dependencias Python
    └── static/
        └── index.html       # Frontend completo con 4 tabs
```

## Endpoints API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Sirve el frontend |
| GET | `/asegurados` | Lista todos los asegurados |
| GET | `/asegurados/{documento}` | Consulta un asegurado por cédula |
| POST | `/asegurados` | Crear asegurado |
| PUT | `/asegurados/{documento}` | Editar asegurado |
| PATCH | `/asegurados/{documento}/estado` | Cambiar estado de póliza |
| DELETE | `/asegurados/{documento}` | Eliminar asegurado |
| POST | `/facturas/escanear` | Extrae datos de imagen con Claude Vision |
| POST | `/reembolsos` | Radica solicitud de reembolso |
| GET | `/reembolsos` | Lista reembolsos (filtro opcional por estado) |
| GET | `/reembolsos/{numero_factura}` | Consulta reembolso por número de factura |
| PATCH | `/reembolsos/{id}/estado` | Cambia estado de un reembolso |
| GET | `/reembolsos/{id}/historial` | Historial de estados de un reembolso |
| DELETE | `/datos` | Reinicia reembolsos (conserva asegurados) |

## Base de datos

- **PostgreSQL 16** en localhost:5432
- Base de datos: `dojo_facturas_db`
- Tablas: `asegurados`, `reembolsos`, `historial_estados`
- Seed automático al iniciar con 3 asegurados de prueba

## Cómo correr

```bash
cd dojo-facturas
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8001
# Abrir http://localhost:8001
# Las tablas y datos de prueba se crean automáticamente al iniciar
```
