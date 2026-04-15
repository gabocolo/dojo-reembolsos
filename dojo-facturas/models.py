from pydantic import BaseModel, field_validator
from datetime import date, datetime


class Asegurado(BaseModel):
    id: int = 0
    tipo_documento: str = "CC"
    documento: str
    nombre: str
    fecha_nacimiento: date | None = None
    genero: str = ""
    email: str = ""
    telefono: str = ""
    numero_poliza: str
    plan: str
    estado_poliza: str
    fecha_inicio_poliza: date | None = None
    fecha_fin_poliza: date | None = None
    fecha_suspension: date | None = None
    periodo_carencia_dias: int = 30
    deducible_anual: float
    deducible_consumido: float
    tope_anual: float
    reembolsado_anual: float
    copago_porcentaje: int
    preexistencias: str = ""
    motivo_estado: str = ""


class CrearAsegurado(BaseModel):
    tipo_documento: str = "CC"
    documento: str
    nombre: str
    fecha_nacimiento: date | None = None
    genero: str = ""
    email: str = ""
    telefono: str = ""
    numero_poliza: str
    plan: str
    fecha_inicio_poliza: date | None = None
    fecha_fin_poliza: date | None = None
    periodo_carencia_dias: int = 30
    deducible_anual: float = 500000
    tope_anual: float = 50000000
    copago_porcentaje: int = 20
    preexistencias: str = ""

    @field_validator("tipo_documento")
    @classmethod
    def tipo_doc_valido(cls, v: str) -> str:
        tipos = ["CC", "CE", "TI", "PP", "NIT"]
        if v.upper() not in tipos:
            raise ValueError(f"Tipo de documento debe ser uno de: {', '.join(tipos)}")
        return v.upper()

    @field_validator("documento")
    @classmethod
    def documento_valido(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El documento no puede estar vacio")
        if len(v) < 6 or len(v) > 12:
            raise ValueError("El documento debe tener entre 6 y 12 caracteres")
        return v

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacio")
        return v.strip()

    @field_validator("copago_porcentaje")
    @classmethod
    def copago_rango(cls, v: int) -> int:
        if v < 0 or v > 30:
            raise ValueError("El copago debe estar entre 0% y 30%")
        return v

    @field_validator("deducible_anual")
    @classmethod
    def deducible_positivo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("El deducible anual no puede ser negativo")
        return v

    @field_validator("tope_anual")
    @classmethod
    def tope_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El tope anual debe ser mayor a cero")
        return v


class EditarAsegurado(BaseModel):
    nombre: str | None = None
    email: str | None = None
    telefono: str | None = None
    plan: str | None = None
    fecha_fin_poliza: date | None = None
    deducible_anual: float | None = None
    tope_anual: float | None = None
    copago_porcentaje: int | None = None
    preexistencias: str | None = None


class CambioEstadoPoliza(BaseModel):
    nuevo_estado: str
    motivo: str = ""

    @field_validator("nuevo_estado")
    @classmethod
    def estado_valido(cls, v: str) -> str:
        estados = ["PENDIENTE_ACTIVACION", "ACTIVA", "SUSPENDIDA", "CANCELADA"]
        if v.upper() not in estados:
            raise ValueError(f"Estado debe ser uno de: {', '.join(estados)}")
        return v.upper()


class SolicitudReembolso(BaseModel):
    numero_factura: str
    documento_asegurado: str
    nit_prestador: str
    nombre_prestador: str
    tipo_servicio: str
    diagnostico_codigo: str = ""
    diagnostico_descripcion: str = ""
    fecha_servicio: date
    valor_factura: float

    @field_validator("numero_factura")
    @classmethod
    def numero_factura_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El número de factura no puede estar vacío")
        return v.strip()

    @field_validator("nit_prestador")
    @classmethod
    def nit_valido(cls, v: str) -> str:
        digitos = v.replace("-", "").replace(".", "").strip()
        if not digitos.isdigit() or not (9 <= len(digitos) <= 10):
            raise ValueError("El NIT del prestador debe tener entre 9 y 10 dígitos")
        return digitos

    @field_validator("valor_factura")
    @classmethod
    def valor_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El valor de la factura debe ser mayor a cero")
        return v

    @field_validator("tipo_servicio")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        tipos = ["CONSULTA", "LABORATORIO", "MEDICAMENTOS", "HOSPITALIZACION", "CIRUGIA"]
        if v.upper() not in tipos:
            raise ValueError(f"Tipo de servicio debe ser uno de: {', '.join(tipos)}")
        return v.upper()


class Reembolso(BaseModel):
    id: str
    numero_factura: str
    documento_asegurado: str
    nit_prestador: str
    nombre_prestador: str
    tipo_servicio: str
    diagnostico_codigo: str
    diagnostico_descripcion: str
    fecha_servicio: date
    fecha_radicacion: datetime
    valor_factura: float
    valor_aprobado: float
    estado: str
    motivo_rechazo: str
    observaciones: str


class CambioEstado(BaseModel):
    nuevo_estado: str
    responsable: str
    observacion: str = ""


class HistorialEstado(BaseModel):
    id: int
    reembolso_id: str
    estado_anterior: str
    estado_nuevo: str
    responsable: str
    fecha: datetime
    observacion: str
