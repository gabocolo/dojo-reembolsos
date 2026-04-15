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
            tipo_documento VARCHAR(5) NOT NULL DEFAULT 'CC',
            documento VARCHAR(20) UNIQUE NOT NULL,
            nombre VARCHAR(200) NOT NULL,
            fecha_nacimiento DATE,
            genero VARCHAR(10) DEFAULT '',
            email VARCHAR(200) DEFAULT '',
            telefono VARCHAR(20) DEFAULT '',
            numero_poliza VARCHAR(50) NOT NULL,
            plan VARCHAR(50) NOT NULL,
            estado_poliza VARCHAR(30) NOT NULL DEFAULT 'ACTIVA',
            fecha_inicio_poliza DATE,
            fecha_fin_poliza DATE,
            fecha_suspension DATE,
            periodo_carencia_dias INTEGER NOT NULL DEFAULT 30,
            deducible_anual NUMERIC(15,2) NOT NULL DEFAULT 0,
            deducible_consumido NUMERIC(15,2) NOT NULL DEFAULT 0,
            tope_anual NUMERIC(15,2) NOT NULL DEFAULT 0,
            reembolsado_anual NUMERIC(15,2) NOT NULL DEFAULT 0,
            copago_porcentaje INTEGER NOT NULL DEFAULT 20,
            preexistencias TEXT DEFAULT '',
            motivo_estado TEXT DEFAULT ''
        )
    """)

    # Migrar columnas nuevas si la tabla ya existia
    nuevas_columnas = [
        ("tipo_documento", "VARCHAR(5) NOT NULL DEFAULT 'CC'"),
        ("fecha_nacimiento", "DATE"),
        ("genero", "VARCHAR(10) DEFAULT ''"),
        ("email", "VARCHAR(200) DEFAULT ''"),
        ("telefono", "VARCHAR(20) DEFAULT ''"),
        ("fecha_inicio_poliza", "DATE"),
        ("fecha_fin_poliza", "DATE"),
        ("fecha_suspension", "DATE"),
        ("periodo_carencia_dias", "INTEGER NOT NULL DEFAULT 30"),
        ("preexistencias", "TEXT DEFAULT ''"),
        ("motivo_estado", "TEXT DEFAULT ''"),
    ]
    conn.commit()
    for col, tipo in nuevas_columnas:
        try:
            cur.execute(f"ALTER TABLE asegurados ADD COLUMN {col} {tipo}")
            conn.commit()
        except Exception:
            conn.rollback()

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
        ("CC", "1017234567", "María López", "1985-03-15", "F", "maria.lopez@email.com", "3001234567",
         "POL-2024-001", "Premium", "ACTIVA", "2024-01-01", "2025-01-01", None, 30,
         500000, 0, 50000000, 0, 20, "", ""),
        ("CC", "1098765432", "Carlos Ruiz", "1990-07-22", "M", "carlos.ruiz@email.com", "3109876543",
         "POL-2024-002", "Básico", "ACTIVA", "2024-03-01", "2025-03-01", None, 30,
         1000000, 0, 20000000, 0, 30, "", ""),
        ("CC", "1045678901", "Ana García", "1978-11-08", "F", "ana.garcia@email.com", "3205678901",
         "POL-2024-003", "Plus", "SUSPENDIDA", "2024-02-01", "2025-02-01", "2024-10-15", 30,
         750000, 0, 35000000, 0, 25, "", "No pago de prima - mora > 30 dias"),
    ]

    for a in asegurados:
        cur.execute("""
            INSERT INTO asegurados (tipo_documento, documento, nombre, fecha_nacimiento, genero,
                email, telefono, numero_poliza, plan, estado_poliza, fecha_inicio_poliza,
                fecha_fin_poliza, fecha_suspension, periodo_carencia_dias,
                deducible_anual, deducible_consumido, tope_anual, reembolsado_anual,
                copago_porcentaje, preexistencias, motivo_estado)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, a)

    conn.commit()
    cur.close()
    conn.close()
