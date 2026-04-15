from pydantic import BaseModel, field_validator
from datetime import date, datetime


class Asegurado(BaseModel):
    id: int = 0
    documento: str
    nombre: str
    numero_poliza: str
    plan: str
    estado_poliza: str
    deducible_anual: float
    deducible_consumido: float
    tope_anual: float
    reembolsado_anual: float
    copago_porcentaje: int


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
