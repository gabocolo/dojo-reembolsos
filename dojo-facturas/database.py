import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": os.getenv("PG_PORT", "5432"),
    "dbname": os.getenv("PG_DATABASE", "dojo_facturas_db"),
    "user": os.getenv("PG_USER", "app_admin"),
    "password": os.getenv("PG_PASSWORD", "dev_password_change_me"),
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Tabla asegurados
    cur.execute("""
        CREATE TABLE IF NOT EXISTS asegurados (
            id SERIAL PRIMARY KEY,
            documento VARCHAR(20) UNIQUE NOT NULL,
            nombre VARCHAR(200) NOT NULL,
            numero_poliza VARCHAR(50) NOT NULL,
            plan VARCHAR(50) NOT NULL,
            estado_poliza VARCHAR(20) NOT NULL DEFAULT 'ACTIVA',
            deducible_anual NUMERIC(15,2) NOT NULL DEFAULT 0,
            deducible_consumido NUMERIC(15,2) NOT NULL DEFAULT 0,
            tope_anual NUMERIC(15,2) NOT NULL DEFAULT 0,
            reembolsado_anual NUMERIC(15,2) NOT NULL DEFAULT 0,
            copago_porcentaje INTEGER NOT NULL DEFAULT 20
        )
    """)

    # Tabla reembolsos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reembolsos (
            id VARCHAR(36) PRIMARY KEY,
            numero_factura VARCHAR(50) UNIQUE NOT NULL,
            documento_asegurado VARCHAR(20) NOT NULL REFERENCES asegurados(documento),
            nit_prestador VARCHAR(20) NOT NULL,
            nombre_prestador VARCHAR(200) NOT NULL,
            tipo_servicio VARCHAR(50) NOT NULL,
            diagnostico_codigo VARCHAR(10) NOT NULL DEFAULT '',
            diagnostico_descripcion VARCHAR(200) NOT NULL DEFAULT '',
            fecha_servicio DATE NOT NULL,
            fecha_radicacion TIMESTAMP NOT NULL DEFAULT NOW(),
            valor_factura NUMERIC(15,2) NOT NULL,
            valor_aprobado NUMERIC(15,2) DEFAULT 0,
            estado VARCHAR(30) NOT NULL DEFAULT 'RADICADO',
            motivo_rechazo TEXT DEFAULT '',
            observaciones TEXT DEFAULT ''
        )
    """)

    # Tabla historial de estados
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historial_estados (
            id SERIAL PRIMARY KEY,
            reembolso_id VARCHAR(36) NOT NULL REFERENCES reembolsos(id),
            estado_anterior VARCHAR(30) NOT NULL,
            estado_nuevo VARCHAR(30) NOT NULL,
            responsable VARCHAR(100) NOT NULL,
            fecha TIMESTAMP NOT NULL DEFAULT NOW(),
            observacion TEXT DEFAULT ''
        )
    """)

    # Eliminar tabla vieja si existe
    cur.execute("DROP TABLE IF EXISTS desembolsos")

    conn.commit()
    cur.close()
    conn.close()


def seed_db():
    conn = get_connection()
    cur = conn.cursor()

    # Solo insertar si no hay datos
    cur.execute("SELECT COUNT(*) FROM asegurados")
    if cur.fetchone()[0] > 0:
        cur.close()
        conn.close()
        return

    asegurados = [
        ("1017234567", "María López", "POL-2024-001", "Premium", "ACTIVA", 500000, 0, 50000000, 0, 20),
        ("1098765432", "Carlos Ruiz", "POL-2024-002", "Básico", "ACTIVA", 1000000, 0, 20000000, 0, 30),
        ("1045678901", "Ana García", "POL-2024-003", "Plus", "SUSPENDIDA", 750000, 0, 35000000, 0, 25),
    ]

    for a in asegurados:
        cur.execute("""
            INSERT INTO asegurados (documento, nombre, numero_poliza, plan, estado_poliza,
                deducible_anual, deducible_consumido, tope_anual, reembolsado_anual, copago_porcentaje)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, a)

    conn.commit()
    cur.close()
    conn.close()
