import json
import uuid
import base64
from datetime import datetime, date
import anthropic
from dotenv import load_dotenv
from models import SolicitudReembolso, Reembolso, Asegurado, HistorialEstado, CrearAsegurado, EditarAsegurado
from database import get_connection

load_dotenv()

# Transiciones válidas de estado
TRANSICIONES = {
    "RADICADO": ["EN_REVISION_DOCUMENTAL"],
    "EN_REVISION_DOCUMENTAL": ["EN_AUDITORIA_MEDICA", "DEVUELTO_POR_DOCUMENTOS"],
    "DEVUELTO_POR_DOCUMENTOS": ["RADICADO"],
    "EN_AUDITORIA_MEDICA": ["EN_VALIDACION_COBERTURA", "RECHAZADO_MEDICO"],
    "EN_VALIDACION_COBERTURA": ["APROBADO", "RECHAZADO_COBERTURA"],
    "APROBADO": ["PAGADO"],
}

PLAZO_RADICACION_DIAS = 30

# Transiciones válidas de estado de póliza
TRANSICIONES_POLIZA = {
    "PENDIENTE_ACTIVACION": ["ACTIVA", "CANCELADA"],
    "ACTIVA": ["SUSPENDIDA", "CANCELADA"],
    "SUSPENDIDA": ["ACTIVA", "CANCELADA"],
}


def _row_to_reembolso(row) -> Reembolso:
    return Reembolso(
        id=row[0],
        numero_factura=row[1],
        documento_asegurado=row[2],
        nit_prestador=row[3],
        nombre_prestador=row[4],
        tipo_servicio=row[5],
        diagnostico_codigo=row[6] or "",
        diagnostico_descripcion=row[7] or "",
        fecha_servicio=row[8],
        fecha_radicacion=row[9],
        valor_factura=float(row[10]),
        valor_aprobado=float(row[11] or 0),
        estado=row[12],
        motivo_rechazo=row[13] or "",
        observaciones=row[14] or "",
    )


ASEGURADO_COLUMNS = """id, tipo_documento, documento, nombre, fecha_nacimiento, genero,
    email, telefono, numero_poliza, plan, estado_poliza, fecha_inicio_poliza,
    fecha_fin_poliza, fecha_suspension, periodo_carencia_dias,
    deducible_anual, deducible_consumido, tope_anual, reembolsado_anual,
    copago_porcentaje, preexistencias, motivo_estado"""


def _row_to_asegurado(row) -> Asegurado:
    return Asegurado(
        id=row[0],
        tipo_documento=row[1] or "CC",
        documento=row[2],
        nombre=row[3],
        fecha_nacimiento=row[4],
        genero=row[5] or "",
        email=row[6] or "",
        telefono=row[7] or "",
        numero_poliza=row[8],
        plan=row[9],
        estado_poliza=row[10],
        fecha_inicio_poliza=row[11],
        fecha_fin_poliza=row[12],
        fecha_suspension=row[13],
        periodo_carencia_dias=row[14] or 30,
        deducible_anual=float(row[15] or 0),
        deducible_consumido=float(row[16] or 0),
        tope_anual=float(row[17] or 0),
        reembolsado_anual=float(row[18] or 0),
        copago_porcentaje=row[19] or 20,
        preexistencias=row[20] or "",
        motivo_estado=row[21] or "",
    )


def _registrar_historial(cur, reembolso_id: str, estado_anterior: str, estado_nuevo: str, responsable: str, observacion: str = ""):
    cur.execute(
        """INSERT INTO historial_estados (reembolso_id, estado_anterior, estado_nuevo, responsable, fecha, observacion)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (reembolso_id, estado_anterior, estado_nuevo, responsable, datetime.now(), observacion),
    )


# === ASEGURADOS ===

def buscar_asegurado(documento: str) -> Asegurado | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT {ASEGURADO_COLUMNS} FROM asegurados WHERE documento = %s", (documento,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return _row_to_asegurado(row) if row else None


def listar_asegurados() -> list[Asegurado]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT {ASEGURADO_COLUMNS} FROM asegurados ORDER BY nombre")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [_row_to_asegurado(r) for r in rows]


def crear_asegurado(datos: CrearAsegurado) -> Asegurado:
    conn = get_connection()
    cur = conn.cursor()

    # Verificar duplicado
    cur.execute("SELECT 1 FROM asegurados WHERE documento = %s", (datos.documento,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise ValueError(f"Ya existe un asegurado con documento {datos.documento}")

    # Verificar póliza duplicada
    cur.execute("SELECT 1 FROM asegurados WHERE numero_poliza = %s", (datos.numero_poliza,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise ValueError(f"Ya existe una póliza con número {datos.numero_poliza}")

    estado_inicial = "ACTIVA" if datos.fecha_inicio_poliza and datos.fecha_inicio_poliza <= date.today() else "PENDIENTE_ACTIVACION"

    cur.execute(
        f"""INSERT INTO asegurados (tipo_documento, documento, nombre, fecha_nacimiento, genero,
            email, telefono, numero_poliza, plan, estado_poliza, fecha_inicio_poliza,
            fecha_fin_poliza, periodo_carencia_dias, deducible_anual, deducible_consumido,
            tope_anual, reembolsado_anual, copago_porcentaje, preexistencias, motivo_estado)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,0,%s,%s,'')
           RETURNING {ASEGURADO_COLUMNS}""",
        (datos.tipo_documento, datos.documento, datos.nombre, datos.fecha_nacimiento,
         datos.genero, datos.email, datos.telefono, datos.numero_poliza, datos.plan,
         estado_inicial, datos.fecha_inicio_poliza, datos.fecha_fin_poliza,
         datos.periodo_carencia_dias, datos.deducible_anual, datos.tope_anual,
         datos.copago_porcentaje, datos.preexistencias),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return _row_to_asegurado(row)


def editar_asegurado(documento: str, datos: EditarAsegurado) -> Asegurado:
    asegurado = buscar_asegurado(documento)
    if not asegurado:
        raise KeyError(f"No se encontró asegurado con documento {documento}")

    campos = []
    valores = []

    if datos.nombre is not None:
        campos.append("nombre = %s")
        valores.append(datos.nombre)
    if datos.email is not None:
        campos.append("email = %s")
        valores.append(datos.email)
    if datos.telefono is not None:
        campos.append("telefono = %s")
        valores.append(datos.telefono)
    if datos.plan is not None:
        campos.append("plan = %s")
        valores.append(datos.plan)
    if datos.fecha_fin_poliza is not None:
        campos.append("fecha_fin_poliza = %s")
        valores.append(datos.fecha_fin_poliza)
    if datos.preexistencias is not None:
        campos.append("preexistencias = %s")
        valores.append(datos.preexistencias)
    if datos.deducible_anual is not None:
        if datos.deducible_anual < asegurado.deducible_consumido:
            raise ValueError(f"No se puede bajar el deducible anual por debajo de lo ya consumido (${asegurado.deducible_consumido:,.0f})")
        campos.append("deducible_anual = %s")
        valores.append(datos.deducible_anual)
    if datos.tope_anual is not None:
        if datos.tope_anual < asegurado.reembolsado_anual:
            raise ValueError(f"No se puede bajar el tope anual por debajo de lo ya reembolsado (${asegurado.reembolsado_anual:,.0f})")
        campos.append("tope_anual = %s")
        valores.append(datos.tope_anual)
    if datos.copago_porcentaje is not None:
        if datos.copago_porcentaje < 0 or datos.copago_porcentaje > 30:
            raise ValueError("El copago debe estar entre 0% y 30%")
        campos.append("copago_porcentaje = %s")
        valores.append(datos.copago_porcentaje)

    if not campos:
        return asegurado

    valores.append(documento)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE asegurados SET {', '.join(campos)} WHERE documento = %s RETURNING {ASEGURADO_COLUMNS}", valores)
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return _row_to_asegurado(row)


def cambiar_estado_poliza(documento: str, nuevo_estado: str, motivo: str = "") -> Asegurado:
    asegurado = buscar_asegurado(documento)
    if not asegurado:
        raise KeyError(f"No se encontró asegurado con documento {documento}")

    estado_actual = asegurado.estado_poliza
    permitidos = TRANSICIONES_POLIZA.get(estado_actual, [])

    if nuevo_estado not in permitidos:
        raise ValueError(f"No se puede pasar de {estado_actual} a {nuevo_estado}. Transiciones válidas: {', '.join(permitidos) if permitidos else 'ninguna (estado final)'}")

    conn = get_connection()
    cur = conn.cursor()

    extras = {"estado_poliza": nuevo_estado, "motivo_estado": motivo}

    if nuevo_estado == "SUSPENDIDA":
        if not motivo:
            cur.close()
            conn.close()
            raise ValueError("Debe indicar el motivo de la suspensión")
        extras["fecha_suspension"] = date.today()

    elif nuevo_estado == "ACTIVA" and estado_actual == "SUSPENDIDA":
        # Reactivación
        extras["fecha_suspension"] = None
        # Si estuvo suspendida > 90 días, resetear contadores
        if asegurado.fecha_suspension:
            dias_suspendida = (date.today() - asegurado.fecha_suspension).days
            if dias_suspendida > 90:
                extras["deducible_consumido"] = 0
                extras["reembolsado_anual"] = 0

    elif nuevo_estado == "CANCELADA":
        if not motivo:
            cur.close()
            conn.close()
            raise ValueError("Debe indicar el motivo de la cancelación")
        # Verificar reembolsos pendientes
        cur.execute(
            "SELECT COUNT(*) FROM reembolsos WHERE documento_asegurado = %s AND estado IN ('RADICADO','EN_REVISION_DOCUMENTAL','EN_AUDITORIA_MEDICA','EN_VALIDACION_COBERTURA')",
            (documento,)
        )
        pendientes = cur.fetchone()[0]
        if pendientes > 0:
            cur.close()
            conn.close()
            raise ValueError(f"No se puede cancelar: hay {pendientes} reembolso(s) en trámite. Resuélvalos primero.")

    set_clause = ", ".join(f"{k} = %s" for k in extras)
    valores = list(extras.values()) + [documento]
    cur.execute(f"UPDATE asegurados SET {set_clause} WHERE documento = %s RETURNING {ASEGURADO_COLUMNS}", valores)
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return _row_to_asegurado(row)


def eliminar_asegurado(documento: str):
    asegurado = buscar_asegurado(documento)
    if not asegurado:
        raise KeyError(f"No se encontró asegurado con documento {documento}")

    conn = get_connection()
    cur = conn.cursor()

    # Verificar que no tenga reembolsos
    cur.execute("SELECT COUNT(*) FROM reembolsos WHERE documento_asegurado = %s", (documento,))
    count = cur.fetchone()[0]
    if count > 0:
        cur.close()
        conn.close()
        raise ValueError(f"No se puede eliminar: el asegurado tiene {count} reembolso(s) asociados")

    cur.execute("DELETE FROM asegurados WHERE documento = %s", (documento,))
    conn.commit()
    cur.close()
    conn.close()


# === RADICAR REEMBOLSO ===

def radicar_reembolso(solicitud: SolicitudReembolso) -> Reembolso:
    # 1. Verificar asegurado existe
    asegurado = buscar_asegurado(solicitud.documento_asegurado)
    if not asegurado:
        raise ValueError(f"No se encontró asegurado con documento {solicitud.documento_asegurado}")

    # 2. Póliza activa
    if asegurado.estado_poliza != "ACTIVA":
        raise ValueError(f"La póliza del asegurado está {asegurado.estado_poliza}. No se puede radicar.")

    # 3. Plazo de radicación (30 días)
    dias = (date.today() - solicitud.fecha_servicio).days
    if dias > PLAZO_RADICACION_DIAS:
        raise ValueError(f"La factura tiene {dias} días desde el servicio. El plazo máximo es {PLAZO_RADICACION_DIAS} días.")

    if dias < 0:
        raise ValueError("La fecha del servicio no puede ser futura.")

    # 4. Factura no duplicada
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM reembolsos WHERE numero_factura = %s", (solicitud.numero_factura,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise ValueError(f"La factura {solicitud.numero_factura} ya fue radicada")

    # Crear reembolso
    reembolso = Reembolso(
        id=str(uuid.uuid4()),
        numero_factura=solicitud.numero_factura,
        documento_asegurado=solicitud.documento_asegurado,
        nit_prestador=solicitud.nit_prestador,
        nombre_prestador=solicitud.nombre_prestador,
        tipo_servicio=solicitud.tipo_servicio,
        diagnostico_codigo=solicitud.diagnostico_codigo,
        diagnostico_descripcion=solicitud.diagnostico_descripcion,
        fecha_servicio=solicitud.fecha_servicio,
        fecha_radicacion=datetime.now(),
        valor_factura=solicitud.valor_factura,
        valor_aprobado=0,
        estado="RADICADO",
        motivo_rechazo="",
        observaciones="",
    )

    cur.execute(
        """INSERT INTO reembolsos (id, numero_factura, documento_asegurado, nit_prestador, nombre_prestador,
            tipo_servicio, diagnostico_codigo, diagnostico_descripcion, fecha_servicio, fecha_radicacion,
            valor_factura, valor_aprobado, estado, motivo_rechazo, observaciones)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (reembolso.id, reembolso.numero_factura, reembolso.documento_asegurado,
         reembolso.nit_prestador, reembolso.nombre_prestador, reembolso.tipo_servicio,
         reembolso.diagnostico_codigo, reembolso.diagnostico_descripcion,
         reembolso.fecha_servicio, reembolso.fecha_radicacion, reembolso.valor_factura,
         reembolso.valor_aprobado, reembolso.estado, reembolso.motivo_rechazo, reembolso.observaciones),
    )

    _registrar_historial(cur, reembolso.id, "", "RADICADO", "Sistema", "Solicitud radicada")
    conn.commit()
    cur.close()
    conn.close()
    return reembolso


# === CAMBIAR ESTADO ===

def cambiar_estado(reembolso_id: str, nuevo_estado: str, responsable: str, observacion: str = "") -> Reembolso:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM reembolsos WHERE id = %s", (reembolso_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        raise KeyError("Reembolso no encontrado")

    reembolso = _row_to_reembolso(row)
    estado_actual = reembolso.estado

    # Validar transición
    permitidos = TRANSICIONES.get(estado_actual, [])
    if nuevo_estado not in permitidos:
        cur.close()
        conn.close()
        raise ValueError(f"No se puede pasar de {estado_actual} a {nuevo_estado}. Transiciones válidas: {', '.join(permitidos)}")

    motivo_rechazo = reembolso.motivo_rechazo
    valor_aprobado = reembolso.valor_aprobado

    # Reglas por estado
    if nuevo_estado == "RECHAZADO_MEDICO":
        if not observacion:
            cur.close()
            conn.close()
            raise ValueError("Debe indicar el motivo del rechazo médico")
        motivo_rechazo = observacion

    elif nuevo_estado == "RECHAZADO_COBERTURA":
        if not observacion:
            cur.close()
            conn.close()
            raise ValueError("Debe indicar el motivo del rechazo de cobertura")
        motivo_rechazo = observacion

    elif nuevo_estado == "APROBADO":
        # Calcular valor aprobado
        asegurado = buscar_asegurado(reembolso.documento_asegurado)
        if not asegurado:
            cur.close()
            conn.close()
            raise ValueError("Asegurado no encontrado")

        # Verificar tope anual
        if asegurado.reembolsado_anual + reembolso.valor_factura > asegurado.tope_anual:
            cur.close()
            conn.close()
            disponible = asegurado.tope_anual - asegurado.reembolsado_anual
            raise ValueError(
                f"Tope anual excedido. Tope: ${asegurado.tope_anual:,.0f}, "
                f"Ya reembolsado: ${asegurado.reembolsado_anual:,.0f}, "
                f"Disponible: ${disponible:,.0f}"
            )

        # Calcular deducible pendiente
        deducible_pendiente = max(0, asegurado.deducible_anual - asegurado.deducible_consumido)
        valor_despues_deducible = max(0, reembolso.valor_factura - deducible_pendiente)

        # Aplicar copago
        copago_decimal = asegurado.copago_porcentaje / 100
        valor_aprobado = round(valor_despues_deducible * (1 - copago_decimal), 2)

        # Actualizar asegurado
        nuevo_deducible_consumido = min(
            asegurado.deducible_anual,
            asegurado.deducible_consumido + min(reembolso.valor_factura, deducible_pendiente)
        )
        cur.execute(
            """UPDATE asegurados SET deducible_consumido = %s, reembolsado_anual = reembolsado_anual + %s
               WHERE documento = %s""",
            (nuevo_deducible_consumido, valor_aprobado, reembolso.documento_asegurado),
        )

        observacion = (
            f"Valor factura: ${reembolso.valor_factura:,.0f} | "
            f"Deducible aplicado: ${min(reembolso.valor_factura, deducible_pendiente):,.0f} | "
            f"Copago {asegurado.copago_porcentaje}% | "
            f"Valor aprobado: ${valor_aprobado:,.0f}"
        )

    # Actualizar reembolso
    cur.execute(
        """UPDATE reembolsos SET estado = %s, motivo_rechazo = %s, valor_aprobado = %s, observaciones = %s
           WHERE id = %s""",
        (nuevo_estado, motivo_rechazo, valor_aprobado, observacion or reembolso.observaciones, reembolso_id),
    )

    _registrar_historial(cur, reembolso_id, estado_actual, nuevo_estado, responsable, observacion)
    conn.commit()

    # Recargar
    cur.execute("SELECT * FROM reembolsos WHERE id = %s", (reembolso_id,))
    reembolso = _row_to_reembolso(cur.fetchone())
    cur.close()
    conn.close()
    return reembolso


# === CONSULTAS ===

def consultar_reembolso(numero_factura: str) -> Reembolso | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reembolsos WHERE numero_factura = %s", (numero_factura,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return _row_to_reembolso(row) if row else None


def listar_reembolsos() -> list[Reembolso]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reembolsos ORDER BY fecha_radicacion DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [_row_to_reembolso(r) for r in rows]


def listar_por_estado(estado: str) -> list[Reembolso]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reembolsos WHERE estado = %s ORDER BY fecha_radicacion DESC", (estado,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [_row_to_reembolso(r) for r in rows]


def historial_reembolso(reembolso_id: str) -> list[HistorialEstado]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM historial_estados WHERE reembolso_id = %s ORDER BY fecha", (reembolso_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [HistorialEstado(id=r[0], reembolso_id=r[1], estado_anterior=r[2], estado_nuevo=r[3],
                            responsable=r[4], fecha=r[5], observacion=r[6] or "") for r in rows]


def reiniciar_datos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM historial_estados")
    cur.execute("DELETE FROM reembolsos")
    cur.execute("UPDATE asegurados SET deducible_consumido = 0, reembolsado_anual = 0")
    conn.commit()
    cur.close()
    conn.close()


# === ESCANEO CON IA ===

def extraer_datos_factura(image_bytes: bytes, media_type: str) -> dict:
    client = anthropic.Anthropic()
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extrae los datos de esta factura médica y responde SOLO con un JSON válido, sin markdown:\n"
                            '{"numero_factura":"...","documento_paciente":"...","nit_prestador":"...","nombre_prestador":"...","tipo_servicio":"...","diagnostico_descripcion":"...","valor_factura":0}\n'
                            "- documento_paciente: solo los dígitos de la cédula o documento del paciente (sin CC, sin puntos)\n"
                            "- tipo_servicio: uno de CONSULTA, LABORATORIO, MEDICAMENTOS, HOSPITALIZACION, CIRUGIA\n"
                            "- nit_prestador: solo dígitos, 9-10 caracteres\n"
                            "- valor_factura: número sin símbolos\n"
                            "Si no encuentras algún campo, usa cadena vacía o 0."
                        ),
                    },
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    # Limpiar markdown si Claude responde con ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return json.loads(raw)
