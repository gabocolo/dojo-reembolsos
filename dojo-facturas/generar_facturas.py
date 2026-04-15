"""Genera facturas médicas de ejemplo como imágenes PNG para probar el escaneo con IA."""

import os
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "facturas_ejemplo")

FACTURAS = [
    {
        "numero": "FAC-2024-001",
        "fecha": "15/03/2024",
        "prestador": "Clínica del Norte S.A.S",
        "nit": "900.111.222-3",
        "direccion": "Cra 43A #1 Sur-100, Medellín",
        "telefono": "(604) 444-5566",
        "paciente": "María López",
        "documento_paciente": "CC 1017234567",
        "servicio": "CONSULTA",
        "descripcion": "Consulta medicina general - Infección aguda de vías respiratorias superiores",
        "codigo_dx": "J06.9",
        "items": [
            ("Consulta medicina general", 1, 150000),
            ("Toma de signos vitales", 1, 30000),
        ],
        "total": 180000,
    },
    {
        "numero": "FAC-2024-047",
        "fecha": "28/03/2024",
        "prestador": "Laboratorio Nacional S.A.",
        "nit": "900.333.444-7",
        "direccion": "Calle 33 #65B-20, Medellín",
        "telefono": "(604) 222-3344",
        "paciente": "Carlos Ruiz",
        "documento_paciente": "CC 1098765432",
        "servicio": "LABORATORIO",
        "descripcion": "Exámenes de laboratorio clínico - Diabetes mellitus tipo 2",
        "codigo_dx": "E11.9",
        "items": [
            ("Hemograma completo", 1, 45000),
            ("Glicemia en ayunas", 1, 25000),
            ("Perfil lipídico completo", 1, 120000),
            ("Hemoglobina glicosilada HbA1c", 1, 85000),
            ("Creatinina sérica", 1, 35000),
            ("Parcial de orina", 1, 20000),
            ("Toma de muestras", 1, 120000),
        ],
        "total": 450000,
    },
    {
        "numero": "FAC-2024-103",
        "fecha": "02/04/2024",
        "prestador": "Dr. Pérez Especialistas S.A.S",
        "nit": "900.555.666-1",
        "direccion": "Cra 48 #10-45 Cons. 301, Medellín",
        "telefono": "(604) 888-9900",
        "paciente": "María López",
        "documento_paciente": "CC 1017234567",
        "servicio": "CIRUGIA",
        "descripcion": "Cirugía menor ambulatoria - Hernia inguinal unilateral",
        "codigo_dx": "K40.9",
        "items": [
            ("Honorarios cirujano", 1, 3500000),
            ("Honorarios anestesiólogo", 1, 1800000),
            ("Uso de quirófano (2 horas)", 1, 1500000),
            ("Insumos quirúrgicos", 1, 950000),
            ("Medicamentos perioperatorios", 1, 450000),
            ("Sala de recuperación", 1, 300000),
        ],
        "total": 8500000,
    },
]


def formato_cop(valor):
    return f"${valor:,.0f}".replace(",", ".")


def cargar_fuentes():
    rutas = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    normal, bold = None, None
    for r in rutas:
        if os.path.exists(r):
            if "bd" in r.lower() or "Bold" in r:
                bold = r
            else:
                normal = r

    try:
        fn_sm = ImageFont.truetype(normal or bold or rutas[0], 14)
        fn_md = ImageFont.truetype(normal or bold or rutas[0], 16)
        fn_lg = ImageFont.truetype(bold or normal or rutas[1], 20)
        fn_xl = ImageFont.truetype(bold or normal or rutas[1], 26)
        fn_title = ImageFont.truetype(bold or normal or rutas[1], 32)
    except OSError:
        fn_sm = ImageFont.load_default()
        fn_md = fn_sm
        fn_lg = fn_sm
        fn_xl = fn_sm
        fn_title = fn_sm

    return fn_sm, fn_md, fn_lg, fn_xl, fn_title


def generar_factura(factura, filename):
    W, H = 850, 1200
    img = Image.new("RGB", (W, H), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    fn_sm, fn_md, fn_lg, fn_xl, fn_title = cargar_fuentes()

    # Colores
    azul = "#1a1a2e"
    gris = "#555555"
    gris_claro = "#888888"
    linea = "#CCCCCC"
    fondo_header = "#1a1a2e"
    verde = "#28a745"

    # === HEADER ===
    draw.rectangle([(0, 0), (W, 100)], fill=fondo_header)
    draw.text((30, 20), factura["prestador"], fill="white", font=fn_xl)
    draw.text((30, 58), f"NIT: {factura['nit']}  |  {factura['direccion']}  |  Tel: {factura['telefono']}", fill="#AAAAAA", font=fn_sm)

    # === TITULO FACTURA ===
    y = 120
    draw.text((30, y), "FACTURA DE VENTA", fill=azul, font=fn_title)
    draw.text((W - 250, y + 5), f"No. {factura['numero']}", fill=azul, font=fn_lg)
    y += 45
    draw.line([(30, y), (W - 30, y)], fill=azul, width=2)

    # === INFO FACTURA ===
    y += 15
    draw.text((30, y), "Fecha de emisión:", fill=gris_claro, font=fn_sm)
    draw.text((170, y), factura["fecha"], fill=azul, font=fn_md)
    draw.text((400, y), "Resolución DIAN:", fill=gris_claro, font=fn_sm)
    draw.text((540, y), "18764-0234 del 01/01/2024", fill=azul, font=fn_sm)

    # === DATOS PACIENTE ===
    y += 40
    draw.rectangle([(30, y), (W - 30, y + 30)], fill="#F0F2F5")
    draw.text((40, y + 6), "DATOS DEL PACIENTE", fill=azul, font=fn_lg)
    y += 40
    draw.text((30, y), "Nombre:", fill=gris_claro, font=fn_sm)
    draw.text((110, y), factura["paciente"], fill=azul, font=fn_md)
    draw.text((400, y), "Documento:", fill=gris_claro, font=fn_sm)
    draw.text((500, y), factura["documento_paciente"], fill=azul, font=fn_md)
    y += 28
    draw.text((30, y), "Diagnóstico:", fill=gris_claro, font=fn_sm)
    draw.text((130, y), f"{factura['codigo_dx']} - {factura['descripcion'].split(' - ')[1] if ' - ' in factura['descripcion'] else factura['descripcion']}", fill=azul, font=fn_sm)

    # === DETALLE SERVICIOS ===
    y += 40
    draw.rectangle([(30, y), (W - 30, y + 30)], fill="#F0F2F5")
    draw.text((40, y + 6), "DETALLE DE SERVICIOS", fill=azul, font=fn_lg)
    y += 38

    # Encabezado tabla
    draw.text((30, y), "Descripción", fill=gris_claro, font=fn_sm)
    draw.text((550, y), "Cant.", fill=gris_claro, font=fn_sm)
    draw.text((650, y), "Valor Unit.", fill=gris_claro, font=fn_sm)
    draw.text((750, y), "Subtotal", fill=gris_claro, font=fn_sm)
    y += 22
    draw.line([(30, y), (W - 30, y)], fill=linea, width=1)
    y += 8

    # Items
    for desc, cant, valor in factura["items"]:
        draw.text((30, y), desc, fill=azul, font=fn_md)
        draw.text((565, y), str(cant), fill=azul, font=fn_md)
        draw.text((640, y), formato_cop(valor), fill=azul, font=fn_md)
        draw.text((740, y), formato_cop(cant * valor), fill=azul, font=fn_md)
        y += 28
        draw.line([(30, y), (W - 30, y)], fill="#EEEEEE", width=1)
        y += 6

    # === TOTAL ===
    y += 10
    draw.line([(500, y), (W - 30, y)], fill=azul, width=2)
    y += 10
    draw.text((500, y), "TOTAL A PAGAR:", fill=azul, font=fn_lg)
    total_text = formato_cop(factura["total"])
    draw.text((700, y), total_text, fill=verde, font=fn_xl)

    # === TIPO DE SERVICIO ===
    y += 50
    draw.text((30, y), "Tipo de servicio:", fill=gris_claro, font=fn_sm)
    draw.text((160, y), factura["servicio"], fill=azul, font=fn_lg)

    # === PIE DE PAGINA ===
    y_footer = H - 120
    draw.line([(30, y_footer), (W - 30, y_footer)], fill=linea, width=1)
    y_footer += 15
    draw.text((30, y_footer), "______________________________", fill=gris, font=fn_sm)
    draw.text((450, y_footer), "______________________________", fill=gris, font=fn_sm)
    y_footer += 22
    draw.text((30, y_footer), "Firma del prestador", fill=gris_claro, font=fn_sm)
    draw.text((450, y_footer), "Firma del paciente", fill=gris_claro, font=fn_sm)
    y_footer += 30
    draw.text((30, y_footer), f"Factura generada como ejemplo para Dojo Tech&Solve  |  {factura['prestador']}  |  NIT {factura['nit']}", fill="#BBBBBB", font=fn_sm)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    img.save(filepath, "PNG")
    print(f"  Generada: {filepath}")
    return filepath


if __name__ == "__main__":
    print("Generando facturas de ejemplo...")
    for i, f in enumerate(FACTURAS):
        nombre = f"factura_{i+1}_{f['servicio'].lower()}.png"
        generar_factura(f, nombre)
    print(f"\n{len(FACTURAS)} facturas generadas en {OUTPUT_DIR}/")
