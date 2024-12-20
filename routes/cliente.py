# routes/cliente.py

from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from database import get_db_connection
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
import os
from decimal import Decimal

cliente_bp = Blueprint('cliente_bp', __name__, url_prefix='/api/cliente')

# routes/cliente.py

@cliente_bp.route('/perfil', methods=['GET'])
@login_required
def obtener_perfil():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = """
            SELECT c.nombre, c.apellido, u.email, c.telefono, c.direccion
            FROM clientes c
            INNER JOIN usuarios u ON c.id_cliente = u.id_cliente
            WHERE u.id_usuario = ?
        """
        cursor.execute(query, (current_user.id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            perfil = {
                'nombre': result.nombre,
                'apellido': result.apellido,
                'email': result.email,
                'telefono': result.telefono,
                'direccion': result.direccion
            }
            return jsonify(perfil), 200
        else:
            return jsonify({'error': 'Perfil no encontrado'}), 404
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500


@cliente_bp.route('/actualizar-perfil', methods=['POST'])
@login_required
def actualizar_perfil():
    data = request.get_json()
    nombre = data.get('nombre')
    apellido = data.get('apellido')
    email = data.get('email')
    telefono = data.get('telefono')
    direccion = data.get('direccion')

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener id_cliente del usuario actual
            query_get_cliente = "SELECT id_cliente FROM usuarios WHERE id_usuario = ?"
            cursor.execute(query_get_cliente, (current_user.id,))
            cliente_result = cursor.fetchone()
            if not cliente_result:
                return jsonify({'error': 'Cliente no encontrado'}), 404
            id_cliente = cliente_result.id_cliente

            # Actualizar email en la tabla usuarios
            query_usuario = "UPDATE usuarios SET email = ? WHERE id_usuario = ?"
            cursor.execute(query_usuario, (email, current_user.id))

            # Actualizar datos en la tabla clientes
            query_cliente = """
                UPDATE clientes SET nombre = ?, apellido = ?, telefono = ?, direccion = ?
                WHERE id_cliente = ?
            """
            cursor.execute(query_cliente, (nombre, apellido, telefono, direccion, id_cliente))

            conn.commit()
            conn.close()
            return jsonify({'message': 'Perfil actualizado exitosamente'}), 200
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Error al actualizar el perfil'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500

@cliente_bp.route('/reservas', methods=['GET'])
@login_required
def obtener_reservas():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener id_cliente del usuario actual
            query_get_cliente = "SELECT id_cliente FROM usuarios WHERE id_usuario = ?"
            cursor.execute(query_get_cliente, (current_user.id,))
            cliente_result = cursor.fetchone()
            if not cliente_result:
                return jsonify({'error': 'Cliente no encontrado'}), 404
            id_cliente = cliente_result.id_cliente

            # Modificar la consulta para excluir los turnos cancelados
            query = """
                SELECT t.id_turno, s.nombre AS servicio, t.fecha, t.hora, t.estado,
                       CASE WHEN p.metodo_pago = 'Pendiente' THEN 'Pendiente' ELSE 'Pagado' END AS pago_estado
                FROM turnos t
                INNER JOIN turno_servicio ts ON t.id_turno = ts.id_turno
                INNER JOIN servicios s ON ts.id_servicio = s.id_servicio
                LEFT JOIN pagos p ON t.id_turno = p.id_turno
                WHERE t.id_cliente = ? AND t.estado != 'Cancelado'
                ORDER BY t.fecha DESC, t.hora DESC
            """
            cursor.execute(query, (id_cliente,))
            results = cursor.fetchall()
            conn.close()
            reservas = []
            for row in results:
                reservas.append({
                    'id_turno': row.id_turno,
                    'servicio': row.servicio,
                    'fecha': row.fecha.strftime('%Y-%m-%d'),
                    'hora': str(row.hora),
                    'estado': row.estado,
                    'pago': row.pago_estado
                })
            return jsonify({'reservas': reservas}), 200
        except Exception as e:
            conn.close()
            print(f"Error en obtener_reservas: {e}")
            return jsonify({'error': 'Error al obtener las reservas'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500

@cliente_bp.route('/cancelar-reserva/<int:id_turno>', methods=['POST'])
@login_required
def cancelar_reserva(id_turno):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Verificar que el turno pertenece al cliente actual
            query_verificar_turno = """
                SELECT id_turno FROM turnos WHERE id_turno = ? AND id_cliente = ?
            """
            cursor.execute(query_verificar_turno, (id_turno, current_user.id_cliente))
            turno_result = cursor.fetchone()
            if not turno_result:
                return jsonify({'error': 'Turno no encontrado o no pertenece al cliente.'}), 404

            # Eliminar registros relacionados en turno_servicio
            query_eliminar_turno_servicio = "DELETE FROM turno_servicio WHERE id_turno = ?"
            cursor.execute(query_eliminar_turno_servicio, (id_turno,))

            # Eliminar registros relacionados en pagos
            query_eliminar_pagos = "DELETE FROM pagos WHERE id_turno = ?"
            cursor.execute(query_eliminar_pagos, (id_turno,))

            # Actualizar el estado del turno a 'Cancelado'
            query_cancelar_turno = "UPDATE turnos SET estado = 'Cancelado' WHERE id_turno = ?"
            cursor.execute(query_cancelar_turno, (id_turno,))

            # Confirmar cambios
            conn.commit()
            conn.close()
            return jsonify({'message': 'Turno cancelado exitosamente.'}), 200
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error en cancelar_reserva: {e}")
            return jsonify({'error': 'Error al cancelar el turno.'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos.'}), 500

@cliente_bp.route('/modificar-reserva/<int:id_turno>', methods=['POST'])
@login_required
def modificar_reserva(id_turno):
    data = request.get_json()
    nueva_fecha = data.get('fecha')
    nueva_hora = data.get('hora')

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Verificar que el turno pertenece al cliente actual
            query_verificar_turno = """
                SELECT t.id_turno, p.metodo_pago
                FROM turnos t
                LEFT JOIN pagos p ON t.id_turno = p.id_turno
                WHERE t.id_turno = ? AND t.id_cliente = ?
            """
            cursor.execute(query_verificar_turno, (id_turno, current_user.id_cliente))
            turno_result = cursor.fetchone()
            if not turno_result:
                return jsonify({'error': 'Turno no encontrado o no pertenece al cliente.'}), 404

            # Verificar que el turno no esté pagado
            metodo_pago = turno_result.metodo_pago
            if metodo_pago and metodo_pago != 'Pendiente':
                return jsonify({'error': 'No se puede modificar un turno pagado.'}), 400

            # Construir la consulta de actualización solo para fecha y hora
            campos_a_actualizar = []
            valores = []

            if nueva_fecha:
                campos_a_actualizar.append("fecha = ?")
                valores.append(nueva_fecha)

            if nueva_hora:
                campos_a_actualizar.append("hora = ?")
                valores.append(nueva_hora)

            if campos_a_actualizar:
                # Actualizar fecha y hora en la tabla turnos
                query_modificar_turno = f"UPDATE turnos SET {', '.join(campos_a_actualizar)} WHERE id_turno = ?"
                valores.append(id_turno)
                cursor.execute(query_modificar_turno, valores)

            conn.commit()
            conn.close()
            return jsonify({'message': 'Turno modificado exitosamente.'}), 200
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error en modificar_reserva: {e}")
            return jsonify({'error': 'Error al modificar el turno.'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos.'}), 500


# Obtener lista de pagos pendientes
@cliente_bp.route('/pagos-pendientes', methods=['GET'])
@login_required
def obtener_pagos_pendientes():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener id_cliente del usuario actual
            query_get_cliente = "SELECT id_cliente FROM usuarios WHERE id_usuario = ?"
            cursor.execute(query_get_cliente, (current_user.id,))
            cliente_result = cursor.fetchone()
            if not cliente_result:
                return jsonify({'error': 'Cliente no encontrado'}), 404
            id_cliente = cliente_result.id_cliente

            # Consultar los pagos pendientes del cliente
            query = """
                SELECT p.id_pago, t.fecha, t.hora, s.nombre AS servicio, p.monto, p.metodo_pago
                FROM pagos p
                JOIN turnos t ON p.id_turno = t.id_turno
                JOIN turno_servicio ts ON t.id_turno = ts.id_turno
                JOIN servicios s ON ts.id_servicio = s.id_servicio
                WHERE t.id_cliente = ? AND p.metodo_pago = 'Pendiente'
            """
            cursor.execute(query, (id_cliente,))
            pagos_pendientes = cursor.fetchall()
            conn.close()

            pagos_list = []
            for pago in pagos_pendientes:
                pagos_list.append({
                    'id_pago': pago.id_pago,
                    'servicio': pago.servicio,
                    'fecha': pago.fecha.strftime('%Y-%m-%d'),
                    'hora': pago.hora.strftime('%H:%M'),
                    'monto': pago.monto,
                    'metodo_pago': pago.metodo_pago
                })
            return jsonify({'pagos_pendientes': pagos_list}), 200
        except Exception as e:
            conn.close()
            return jsonify({'error': 'Error al obtener los pagos pendientes'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500


# Realizar pago de una reserva individual
@cliente_bp.route('/pagar-reserva/<int:id_pago>', methods=['POST'])
@login_required
def realizar_pago(id_pago):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener los datos enviados desde el frontend
            data = request.get_json()
            tipo_tarjeta = data.get('tipo', '').lower()  # 'credito' o 'debito'
            apply_discount = data.get('applyDiscount', False)  # Recibir si se aplica descuento

            # Validar el tipo de tarjeta
            if tipo_tarjeta not in ['credito', 'debito']:
                return jsonify({'error': 'Tipo de tarjeta inválido.'}), 400

            # Mapear el tipo de tarjeta a la descripción completa
            metodo_pago = 'Tarjeta de Crédito' if tipo_tarjeta == 'credito' else 'Tarjeta de Débito'

            # Obtener el monto original del pago
            query_get_pago = """
                SELECT p.monto, t.id_cliente
                FROM pagos p
                JOIN turnos t ON p.id_turno = t.id_turno
                WHERE p.id_pago = ?
            """
            cursor.execute(query_get_pago, (id_pago,))
            pago_result = cursor.fetchone()
            if not pago_result:
                conn.rollback()
                return jsonify({'error': 'Pago no encontrado'}), 404
            monto_original, id_cliente = pago_result

            # Convertir monto a Decimal para precisión en cálculos monetarios
            monto = Decimal(monto_original)

            # Aplicar descuento si corresponde
            if apply_discount:
                monto = monto * Decimal('0.9')  # Aplicar 10% de descuento

            # Actualizar el método de pago y el monto en la tabla pagos
            query_actualizar_pago = "UPDATE pagos SET metodo_pago = ?, monto = ? WHERE id_pago = ?"
            cursor.execute(query_actualizar_pago, (metodo_pago, float(monto), id_pago))

            # Insertar factura con el monto con descuento
            query_insertar_factura = """
                INSERT INTO facturas (id_cliente, id_pago, total)
                VALUES (?, ?, ?)
            """
            cursor.execute(query_insertar_factura, (id_cliente, id_pago, float(monto)))

            conn.commit()
            conn.close()
            return jsonify({'message': 'Pago realizado y factura generada exitosamente'}), 200
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error en realizar_pago: {e}")  # Para depuración
            return jsonify({'error': 'Error al procesar el pago'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500


# Obtener lista de pagos realizados
@cliente_bp.route('/pagos-realizados', methods=['GET'])
@login_required
def obtener_pagos_realizados():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener id_cliente del usuario actual
            query_get_cliente = "SELECT id_cliente FROM usuarios WHERE id_usuario = ?"
            cursor.execute(query_get_cliente, (current_user.id,))
            cliente_result = cursor.fetchone()
            if not cliente_result:
                return jsonify({'error': 'Cliente no encontrado'}), 404
            id_cliente = cliente_result.id_cliente

            # Consultar los pagos realizados del cliente
            query = """
                SELECT f.id_factura, t.fecha, t.hora, s.nombre AS servicio, f.total
                FROM facturas f
                JOIN pagos p ON f.id_pago = p.id_pago
                JOIN turnos t ON p.id_turno = t.id_turno
                JOIN turno_servicio ts ON t.id_turno = ts.id_turno
                JOIN servicios s ON ts.id_servicio = s.id_servicio
                WHERE f.id_cliente = ?
                ORDER BY f.fecha_emision DESC
            """
            cursor.execute(query, (id_cliente,))
            pagos_realizados = cursor.fetchall()
            conn.close()

            pagos_list = []
            for pago in pagos_realizados:
                pagos_list.append({
                    'id_factura': pago.id_factura,
                    'servicio': pago.servicio,
                    'fecha': pago.fecha.strftime('%Y-%m-%d'),
                    'hora': pago.hora.strftime('%H:%M'),
                    'total': pago.total
                })
            return jsonify({'pagos_realizados': pagos_list}), 200
        except Exception as e:
            conn.close()
            return jsonify({'error': 'Error al obtener los pagos realizados'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500
    
@cliente_bp.route('/factura/<int:id_factura>', methods=['GET'])
@login_required
def generar_factura(id_factura):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = """
            SELECT f.id_factura, f.fecha_emision, t.fecha AS fecha_servicio, t.hora, 
                   s.nombre AS servicio, f.total, c.nombre AS cliente_nombre, 
                   c.apellido AS cliente_apellido, p.metodo_pago
            FROM facturas f
            JOIN pagos p ON f.id_pago = p.id_pago
            JOIN turnos t ON p.id_turno = t.id_turno
            JOIN turno_servicio ts ON t.id_turno = ts.id_turno
            JOIN servicios s ON ts.id_servicio = s.id_servicio
            JOIN clientes c ON f.id_cliente = c.id_cliente
            WHERE f.id_factura = ? AND t.id_cliente = ?
        """
        cursor.execute(query, (id_factura, current_user.id_cliente))
        factura = cursor.fetchone()
        conn.close()

        if not factura:
            return jsonify({'error': 'Factura no encontrada.'}), 404

        factura_id, fecha_emision, fecha_servicio, hora_servicio, servicio, total, cliente_nombre, cliente_apellido, metodo_pago = factura
        filename = f'factura_{factura_id}.pdf'
        filepath = os.path.join('facturas', filename)

        if not os.path.exists('facturas'):
            os.makedirs('facturas')

        # Configuración del documento
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()

        styles['Normal'].fontSize = 12
        styles['Title'].fontSize = 16

        elements = []

        # Agregar logo
        logo_path = os.path.join('static', 'logo.png')
        if os.path.exists(logo_path):
            im = Image(logo_path, width=120, height=60)
            elements.append(im)

        # Encabezado de la factura
        elements.append(Spacer(1, 12))
        title = Paragraph(f"<para align='right'><b>Factura N° {factura_id}</b></para>", styles['Title'])
        elements.append(title)

        empresa_info = Paragraph("""
            <b>Spa Sentirse Bien</b><br/>
            Dirección: Calle Falsa 123, Ciudad<br/>
            Teléfono: 123-456-7890<br/>
            Email: info@sentirsebien.com
            """, styles['Normal'])
        elements.append(empresa_info)

        elements.append(Spacer(1, 12))

        # Información del cliente
        cliente_info = Paragraph(f"<b>Cliente:</b> {cliente_nombre} {cliente_apellido}", styles['Normal'])
        elements.append(cliente_info)

        fecha_info = Paragraph(f"<b>Fecha de emisión:</b> {fecha_emision.strftime('%Y-%m-%d')}", styles['Normal'])
        metodo_pago_info = Paragraph(f"<b>Método de pago:</b> {metodo_pago.capitalize()}", styles['Normal'])
        elements.append(fecha_info)
        elements.append(metodo_pago_info)

        elements.append(Spacer(1, 12))

        # Detalles del servicio en una tabla
        data = [
            ['Descripción', 'Fecha del Servicio', 'Hora', 'Cantidad', 'Precio Unitario', 'Total'],
            [servicio, fecha_servicio.strftime('%Y-%m-%d'), hora_servicio.strftime('%H:%M'), '1', f"${total:.2f}", f"${total:.2f}"]
        ]

        table = Table(data, colWidths=[150, 90, 50, 60, 80, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4A90E2")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 12))

        # Resumen del pago (eliminamos impuestos)
        resumen_data = [
            ['Subtotal:', f"${total:.2f}"],
            ['Total Pagado:', f"${total:.2f}"]
        ]

        resumen_table = Table(resumen_data, colWidths=[400, 100])
        resumen_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(resumen_table)

        elements.append(Spacer(1, 24))

        # Pie de página
        footer = Paragraph("Gracias por confiar en nosotros. ¡Esperamos verte pronto!", styles['Normal'])
        elements.append(footer)

        # Generar el documento PDF
        doc.build(elements)

        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({'error': 'Error de conexión a la base de datos.'}), 500

    
# Realizar pagos de todos los pendientes
@cliente_bp.route('/pagar-todos', methods=['POST'])
@login_required
def pagar_todos():
    data = request.get_json()
    tipo_tarjeta = data.get('tipo', '').lower()  # 'credito' o 'debito'

    # Validar el tipo de tarjeta
    if tipo_tarjeta not in ['credito', 'debito']:
        return jsonify({'error': 'Tipo de tarjeta inválido.'}), 400

    # Mapear el tipo de tarjeta a la descripción completa
    metodo_pago = 'Tarjeta de Crédito' if tipo_tarjeta == 'credito' else 'Tarjeta de Débito'

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener id_cliente del usuario actual
            query_get_cliente = "SELECT id_cliente FROM usuarios WHERE id_usuario = ?"
            cursor.execute(query_get_cliente, (current_user.id,))
            cliente_result = cursor.fetchone()
            if not cliente_result:
                return jsonify({'error': 'Cliente no encontrado'}), 404
            id_cliente = cliente_result.id_cliente

            # Obtener todos los pagos pendientes del cliente
            query_pagos_pendientes = """
                SELECT p.id_pago, p.monto
                FROM pagos p
                JOIN turnos t ON p.id_turno = t.id_turno
                WHERE t.id_cliente = ? AND p.metodo_pago = 'Pendiente'
            """
            cursor.execute(query_pagos_pendientes, (id_cliente,))
            pagos_pendientes = cursor.fetchall()

            if not pagos_pendientes:
                return jsonify({'error': 'No hay pagos pendientes.'}), 400

            facturas_generadas = []

            # Procesar el pago de cada reserva pendiente
            for pago in pagos_pendientes:
                id_pago, monto = pago

                # Actualizar el método de pago
                query_actualizar_pago = "UPDATE pagos SET metodo_pago = ? WHERE id_pago = ?"
                cursor.execute(query_actualizar_pago, (metodo_pago, id_pago,))

                # Insertar una factura para cada pago y recuperar el id_factura generado
                query_insertar_factura = """
                    INSERT INTO facturas (id_cliente, id_pago, total)
                    OUTPUT INSERTED.id_factura
                    VALUES (?, ?, ?)
                """
                cursor.execute(query_insertar_factura, (id_cliente, id_pago, monto))
                id_factura = cursor.fetchone()[0]  # Recupera el id_factura generado

                # Agregar detalles de la factura a la lista generada
                facturas_generadas.append({
                    'id_factura': id_factura,
                    'servicio': 'Servicio Desconocido',  # Ajusta según tu lógica
                    'fecha': 'Fecha Desconocida',       # Ajusta según tu lógica
                    'hora': 'Hora Desconocida',         # Ajusta según tu lógica
                    'total': monto
                })

            conn.commit()  # Confirmar los cambios
            cursor.close()
            conn.close()
            return jsonify({
                'message': 'Todos los pagos realizados y facturas generadas exitosamente.',
                'facturas': facturas_generadas
            }), 200

        except Exception as e:
            conn.rollback()  # Revertir cambios en caso de error
            cursor.close()
            conn.close()
            print(f"Error en pagar_todos: {e}")  # Para depuración
            return jsonify({'error': 'Error al procesar los pagos.'}), 500

    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500

@cliente_bp.route('/servicios', methods=['GET'])
@login_required
def obtener_servicios():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            query = "SELECT id_servicio, nombre, duracion FROM servicios"
            cursor.execute(query)
            servicios = cursor.fetchall()
            conn.close()
            servicios_list = []
            for servicio in servicios:
                servicios_list.append({
                    'id_servicio': servicio.id_servicio,
                    'nombre': servicio.nombre,
                    'duracion': servicio.duracion
                })
            return jsonify({'servicios': servicios_list}), 200
        except Exception as e:
            conn.close()
            return jsonify({'error': 'Error al obtener los servicios'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500
    
@cliente_bp.route('/reserva/<int:id_turno>', methods=['GET'])
@login_required
def obtener_reserva(id_turno):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            query = """
                SELECT t.fecha, t.hora, ts.id_servicio, s.nombre AS nombre_servicio
                FROM turnos t
                INNER JOIN turno_servicio ts ON t.id_turno = ts.id_turno
                INNER JOIN servicios s ON ts.id_servicio = s.id_servicio
                WHERE t.id_turno = ? AND t.id_cliente = ?
            """
            cursor.execute(query, (id_turno, current_user.id_cliente))
            reserva = cursor.fetchone()
            conn.close()
            if reserva:
                return jsonify({
                    'fecha': reserva.fecha.strftime('%Y-%m-%d'),
                    'hora': reserva.hora.strftime('%H:%M'),
                    'id_servicio': reserva.id_servicio,
                    'nombre_servicio': reserva.nombre_servicio
                }), 200
            else:
                return jsonify({'error': 'Reserva no encontrada.'}), 404
        except Exception as e:
            conn.close()
            print(f"Error en obtener_reserva: {e}")
            return jsonify({'error': 'Error al obtener la reserva.'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos.'}), 500