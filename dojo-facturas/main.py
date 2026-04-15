from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from models import SolicitudReembolso, Reembolso, CambioEstado, Asegurado, HistorialEstado
from services import (
    radicar_reembolso, consultar_reembolso, cambiar_estado, listar_reembolsos,
    listar_por_estado, historial_reembolso, listar_asegurados, buscar_asegurado,
    extraer_datos_factura, reiniciar_datos,
)
from database import init_db, seed_db

app = FastAPI(title="Sistema de Reembolsos Médicos")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def startup():
    init_db()
    seed_db()


@app.get("/")
def root():
    return FileResponse(static_dir / "index.html")


# === ASEGURADOS ===

@app.get("/asegurados", response_model=list[Asegurado])
def get_asegurados():
    return listar_asegurados()


@app.get("/asegurados/{documento}", response_model=Asegurado)
def get_asegurado(documento: str):
    asegurado = buscar_asegurado(documento)
    if not asegurado:
        raise HTTPException(status_code=404, detail="Asegurado no encontrado")
    return asegurado


# === ESCANEO ===

@app.post("/facturas/escanear")
async def escanear_factura(archivo: UploadFile = File(...)):
    tipos_permitidos = ["image/png", "image/jpeg", "image/webp", "image/gif"]
    if archivo.content_type not in tipos_permitidos:
        raise HTTPException(status_code=400, detail="Formato no soportado. Usa PNG, JPG, WEBP o GIF")
    image_bytes = await archivo.read()
    try:
        return extraer_datos_factura(image_bytes, archivo.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {str(e)}")


# === REEMBOLSOS ===

@app.post("/reembolsos", response_model=Reembolso)
def crear_reembolso(solicitud: SolicitudReembolso):
    try:
        return radicar_reembolso(solicitud)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reembolsos", response_model=list[Reembolso])
def get_reembolsos(estado: str = Query(None)):
    if estado:
        return listar_por_estado(estado)
    return listar_reembolsos()


@app.get("/reembolsos/{numero_factura}", response_model=Reembolso)
def get_reembolso(numero_factura: str):
    reembolso = consultar_reembolso(numero_factura)
    if not reembolso:
        raise HTTPException(status_code=404, detail="Reembolso no encontrado")
    return reembolso


@app.patch("/reembolsos/{reembolso_id}/estado", response_model=Reembolso)
def actualizar_estado(reembolso_id: str, cambio: CambioEstado):
    try:
        return cambiar_estado(reembolso_id, cambio.nuevo_estado, cambio.responsable, cambio.observacion)
    except KeyError:
        raise HTTPException(status_code=404, detail="Reembolso no encontrado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/reembolsos/{reembolso_id}/historial", response_model=list[HistorialEstado])
def get_historial(reembolso_id: str):
    return historial_reembolso(reembolso_id)


# === ADMIN ===

@app.delete("/datos")
def borrar_datos():
    reiniciar_datos()
    return {"mensaje": "Datos reiniciados (asegurados conservados)"}
