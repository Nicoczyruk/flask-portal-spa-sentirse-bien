# backend/routes/informes.py

from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required
from database import get_db_connection
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os
from decimal import Decimal
from datetime import datetime

import tempfile  # Para manejo de archivos temporales

informes_bp = Blueprint('informes_bp', __name__, url_prefix='/api/informes')

# Función para convertir fecha de DD/MM/AAAA a YYYY-MM-DD
def convertir_fecha(fecha_str):
    try:
        return datetime.strptime(fecha_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError as e:
        print(f"Error convirtiendo la fecha: {fecha_str}, error: {e}")
        return None

# Función para sanitizar el nombre del archivo
def sanitizar_nombre_archivo(fecha_inicio, fecha_fin):
    # Reemplazar '/' con '-' en las fechas
    fecha_inicio_safe = fecha_inicio.replace('/', '-')
    fecha_fin_safe = fecha_fin.replace('/', '-')
    return fecha_inicio_safe, fecha_fin_safe

# Informe de ingresos por tipo de pago en un rango de fechas
@informes_bp.route('/ingresos', methods=['POST'])
@login_required
def generar_informe_ingresos():
    data = request.get_json()
    fecha_inicio_original = data.get('fecha_inicio')
    fecha_fin_original = data.get('fecha_fin')
    
    fecha_inicio = convertir_fecha(fecha_inicio_original)
    fecha_fin = convertir_fecha(fecha_fin_original)

    if not fecha_inicio or not fecha_fin:
        return jsonify({
            'error': 'Formato de fecha incorrecto. Debe ser DD/MM/AAAA.',
            'fecha_inicio_original': fecha_inicio_original,
            'fecha_fin_original': fecha_fin_original
        }), 400

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                SELECT p.metodo_pago, SUM(p.monto) AS total
                FROM pagos p
                WHERE p.fecha_pago BETWEEN ? AND ?
                GROUP BY p.metodo_pago
            """
            cursor.execute(query, (fecha_inicio, fecha_fin))
            ingresos = cursor.fetchall()

            # Devolver los datos como JSON para mostrarlos en el frontend
            resultados = [{'metodo_pago': row.metodo_pago, 'total': f"{row.total:.2f}"} for row in ingresos]
            return jsonify(resultados), 200
        except Exception as e:
            print(f"Error ejecutando la consulta de ingresos: {e}")
            return jsonify({'error': 'Error al ejecutar la consulta de ingresos.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'error': 'Error al conectar con la base de datos.'}), 500

# Ruta para generar y descargar el PDF de ingresos
@informes_bp.route('/ingresos-pdf', methods=['POST'])
@login_required
def descargar_informe_ingresos_pdf():
    data = request.get_json()
    fecha_inicio_original = data.get('fecha_inicio')
    fecha_fin_original = data.get('fecha_fin')
    
    fecha_inicio = convertir_fecha(fecha_inicio_original)
    fecha_fin = convertir_fecha(fecha_fin_original)

    if not fecha_inicio or not fecha_fin:
        return jsonify({
            'error': 'Formato de fecha incorrecto. Debe ser DD/MM/AAAA.',
            'fecha_inicio_original': fecha_inicio_original,
            'fecha_fin_original': fecha_fin_original
        }), 400

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                SELECT p.metodo_pago, SUM(p.monto) AS total
                FROM pagos p
                WHERE p.fecha_pago BETWEEN ? AND ?
                GROUP BY p.metodo_pago
            """
            cursor.execute(query, (fecha_inicio, fecha_fin))
            ingresos = cursor.fetchall()

            # Sanitizar los nombres de archivo
            fecha_inicio_safe, fecha_fin_safe = sanitizar_nombre_archivo(fecha_inicio_original, fecha_fin_original)

            # Crear el archivo PDF en un directorio temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'_ingresos_{fecha_inicio_safe}_a_{fecha_fin_safe}.pdf') as tmp_file:
                filepath = tmp_file.name

            crear_informe_ingresos_pdf(ingresos, fecha_inicio_original, fecha_fin_original, filepath)

            return send_file(filepath, as_attachment=True)
        except Exception as e:
            print(f"Error generando el PDF de ingresos: {e}")
            return jsonify({'error': 'Error al generar el PDF de ingresos.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'error': 'Error al conectar con la base de datos.'}), 500

def crear_informe_ingresos_pdf(ingresos, fecha_inicio, fecha_fin, filepath):
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()

    # Encabezado del documento
    elements = []
    elements.append(Paragraph(f"Informe de Ingresos - {fecha_inicio} a {fecha_fin}", styles['Title']))
    
    logo_path = os.path.join('static', 'logo.png')
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=60))
    
    elements.append(Spacer(1, 12))

    # Tabla de ingresos por tipo de pago
    data = [['Método de Pago', 'Total Ingresos']]
    for row in ingresos:
        data.append([row.metodo_pago, f"${Decimal(row.total):.2f}"])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
    ]))

    elements.append(table)
    doc.build(elements)

# Informe de servicios realizados por profesional
@informes_bp.route('/servicios-profesional', methods=['POST'])
@login_required
def generar_informe_servicios_profesional():
    data = request.get_json()
    fecha_inicio_original = data.get('fecha_inicio')
    fecha_fin_original = data.get('fecha_fin')
    
    fecha_inicio = convertir_fecha(fecha_inicio_original)
    fecha_fin = convertir_fecha(fecha_fin_original)

    if not fecha_inicio or not fecha_fin:
        return jsonify({
            'error': 'Formato de fecha incorrecto. Debe ser DD/MM/AAAA.',
            'fecha_inicio_original': fecha_inicio_original,
            'fecha_fin_original': fecha_fin_original
        }), 400

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                SELECT p.nombre, p.apellido, s.nombre AS servicio, COUNT(t.id_turno) AS total_servicios
                FROM turnos t
                JOIN profesionales p ON t.id_profesional = p.id_profesional
                JOIN turno_servicio ts ON t.id_turno = ts.id_turno
                JOIN servicios s ON ts.id_servicio = s.id_servicio
                WHERE t.fecha BETWEEN ? AND ?
                GROUP BY p.nombre, p.apellido, s.nombre
            """
            cursor.execute(query, (fecha_inicio, fecha_fin))
            servicios = cursor.fetchall()

            # Devolver los datos como JSON para mostrarlos en el frontend
            resultados = [{'nombre': row.nombre, 'apellido': row.apellido, 'servicio': row.servicio, 'total_servicios': row.total_servicios} for row in servicios]
            return jsonify(resultados), 200
        except Exception as e:
            print(f"Error ejecutando la consulta de servicios por profesional: {e}")
            return jsonify({'error': 'Error al ejecutar la consulta de servicios por profesional.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'error': 'Error al conectar con la base de datos.'}), 500

# Ruta para generar y descargar el PDF de servicios por profesional
@informes_bp.route('/servicios-profesional-pdf', methods=['POST'])
@login_required
def descargar_informe_servicios_profesional_pdf():
    data = request.get_json()
    fecha_inicio_original = data.get('fecha_inicio')
    fecha_fin_original = data.get('fecha_fin')
    
    fecha_inicio = convertir_fecha(fecha_inicio_original)
    fecha_fin = convertir_fecha(fecha_fin_original)

    if not fecha_inicio or not fecha_fin:
        return jsonify({
            'error': 'Formato de fecha incorrecto. Debe ser DD/MM/AAAA.',
            'fecha_inicio_original': fecha_inicio_original,
            'fecha_fin_original': fecha_fin_original
        }), 400

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                SELECT p.nombre, p.apellido, s.nombre AS servicio, COUNT(t.id_turno) AS total_servicios
                FROM turnos t
                JOIN profesionales p ON t.id_profesional = p.id_profesional
                JOIN turno_servicio ts ON t.id_turno = ts.id_turno
                JOIN servicios s ON ts.id_servicio = s.id_servicio
                WHERE t.fecha BETWEEN ? AND ?
                GROUP BY p.nombre, p.apellido, s.nombre
            """
            cursor.execute(query, (fecha_inicio, fecha_fin))
            servicios = cursor.fetchall()

            # Sanitizar los nombres de archivo
            fecha_inicio_safe, fecha_fin_safe = sanitizar_nombre_archivo(fecha_inicio_original, fecha_fin_original)

            # Crear el archivo PDF en un directorio temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'_servicios_profesional_{fecha_inicio_safe}_a_{fecha_fin_safe}.pdf') as tmp_file:
                filepath = tmp_file.name

            crear_informe_servicios_pdf(servicios, fecha_inicio_original, fecha_fin_original, filepath)

            return send_file(filepath, as_attachment=True)
        except Exception as e:
            print(f"Error generando el PDF de servicios por profesional: {e}")
            return jsonify({'error': 'Error al generar el PDF de servicios por profesional.'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'error': 'Error al conectar con la base de datos.'}), 500

def crear_informe_servicios_pdf(servicios, fecha_inicio, fecha_fin, filepath):
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph(f"Informe de Servicios por Profesional - {fecha_inicio} a {fecha_fin}", styles['Title']))

    logo_path = os.path.join('static', 'logo.png')
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=60))
    
    elements.append(Spacer(1, 12))

    data = [['Profesional', 'Servicio', 'Total Servicios']]
    for row in servicios:
        data.append([f"{row.nombre} {row.apellido}", row.servicio, row.total_servicios])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')
    ]))

    elements.append(table)
    doc.build(elements)

# Función para sanitizar el nombre del archivo
def sanitizar_nombre_archivo(fecha_inicio, fecha_fin):
    # Reemplazar '/' con '-' en las fechas
    fecha_inicio_safe = fecha_inicio.replace('/', '-')
    fecha_fin_safe = fecha_fin.replace('/', '-')
    return fecha_inicio_safe, fecha_fin_safe
