from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from database import get_db_connection
from datetime import datetime, timedelta
from random import choice

reservas_bp = Blueprint('reservas_bp', __name__, url_prefix='/api/reservas')

@reservas_bp.route('/horas-reservadas/<fecha>', methods=['GET'])
@login_required
def obtener_horas_reservadas(fecha):
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD.'}), 400

    if not current_user.id_cliente:
        return jsonify({'error': 'Usuario no asociado a un cliente.'}), 403

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = """
            SELECT hora 
            FROM turnos 
            WHERE fecha = ? AND estado = 'Pendiente'
        """
        cursor.execute(query, (fecha_obj,))
        resultados = cursor.fetchall()
        conn.close()
        horas_reservadas = [fila.hora.strftime('%H:%M') for fila in resultados]
        return jsonify({'horas_reservadas': horas_reservadas}), 200
    else:
        return jsonify({'error': 'Error de conexión a la base de datos.'}), 500

@reservas_bp.route('/crear', methods=['POST'])
@login_required
def crear_reserva():
    data = request.get_json()
    fecha = data.get('fecha')
    hora = data.get('hora')
    id_servicio = data.get('id_servicio')
    
    if not fecha or not hora or not id_servicio:
        return jsonify({'error': 'Faltan datos necesarios para la reserva.'}), 400
    
    if not current_user.id_cliente:
        return jsonify({'error': 'Usuario no asociado a un cliente.'}), 403
    
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        hora_obj = datetime.strptime(hora, '%H:%M').time()
    except ValueError:
        return jsonify({'error': 'Formato de fecha u hora inválido.'}), 400
    
    ahora = datetime.now()
    reserva_datetime = datetime.combine(fecha_obj, hora_obj)
    diferencia = reserva_datetime - ahora
    if diferencia < timedelta(hours=72):
        return jsonify({'error': 'Las reservas deben realizarse con al menos 72 horas de anticipación.'}), 400
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Verificar si la hora ya está reservada
            query_verificar = """
                SELECT * 
                FROM turnos 
                WHERE fecha = ? AND hora = ? AND estado = 'Pendiente'
            """
            cursor.execute(query_verificar, (fecha_obj, hora_obj))
            turno_existente = cursor.fetchone()
            if turno_existente:
                conn.close()
                return jsonify({'error': 'La hora seleccionada ya está reservada.'}), 400
            
            # Asignar un profesional disponible (seleccionamos el primero disponible)
            cursor.execute("SELECT id_profesional FROM profesionales")
            profesionales = cursor.fetchall()
            if not profesionales:
                conn.close()
                return jsonify({'error': 'No hay profesionales disponibles.'}), 400
            id_profesional = choice([p[0] for p in profesionales])
            
            # Insertar la nueva reserva en la tabla turnos y obtener el id_turno generado
            query_insertar_turno = """
                INSERT INTO turnos (fecha, hora, id_cliente, id_profesional, estado)
                OUTPUT INSERTED.id_turno
                VALUES (?, ?, ?, ?, 'Pendiente')
            """
            cursor.execute(query_insertar_turno, (fecha_obj, hora_obj, current_user.id_cliente, id_profesional))
            id_turno = cursor.fetchone()[0]
            
            if not id_turno:
                conn.rollback()
                conn.close()
                return jsonify({'error': 'Error al obtener el ID del turno.'}), 500

            # Insertar la relación en turno_servicio
            query_insertar_turno_servicio = """
                INSERT INTO turno_servicio (id_turno, id_servicio)
                VALUES (?, ?)
            """
            cursor.execute(query_insertar_turno_servicio, (id_turno, id_servicio))
            
            # Insertar un pago pendiente en la tabla pagos
            cursor.execute("SELECT precio FROM servicios WHERE id_servicio = ?", (id_servicio,))
            servicio = cursor.fetchone()
            if not servicio:
                conn.rollback()
                conn.close()
                return jsonify({'error': 'Servicio no encontrado.'}), 400
            precio = servicio[0]
            
            query_insertar_pago = """
                INSERT INTO pagos (id_turno, monto, metodo_pago)
                VALUES (?, ?, 'Pendiente')
            """
            cursor.execute(query_insertar_pago, (id_turno, precio))
            
            conn.commit()
            conn.close()
            return jsonify({'mensaje': 'Reserva creada exitosamente.'}), 201
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error al crear la reserva: {e}")
            return jsonify({'error': 'Error al crear la reserva.'}), 500
    else:
        return jsonify({'error': 'Error de conexión a la base de datos.'}), 500


@reservas_bp.route('/historial', methods=['GET'])
@login_required
def historial_reservas():
    if not current_user.id_cliente:
        return jsonify({'error': 'Usuario no asociado a un cliente.'}), 403

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        # Parámetro de referencia de 48 horas para la comparación
        cutoff_date = "DATEADD(HOUR, -48, GETDATE())"

        # Eliminar dependencias de turnos no pagados y anteriores a 48 horas
        try:
            # Eliminar de turno_servicio
            query_eliminar_turno_servicio = f"""
                DELETE FROM turno_servicio
                WHERE id_turno IN (
                    SELECT t.id_turno
                    FROM turnos t
                    LEFT JOIN pagos p ON t.id_turno = p.id_turno
                    WHERE DATEADD(SECOND, DATEDIFF(SECOND, 0, t.hora), CAST(t.fecha AS DATETIME)) < {cutoff_date}
                    AND (p.metodo_pago IS NULL OR p.metodo_pago = 'Pendiente')
                )
            """
            cursor.execute(query_eliminar_turno_servicio)

            # Eliminar de pagos
            query_eliminar_pagos = f"""
                DELETE FROM pagos
                WHERE id_turno IN (
                    SELECT t.id_turno
                    FROM turnos t
                    LEFT JOIN pagos p ON t.id_turno = p.id_turno
                    WHERE DATEADD(SECOND, DATEDIFF(SECOND, 0, t.hora), CAST(t.fecha AS DATETIME)) < {cutoff_date}
                    AND (p.metodo_pago IS NULL OR p.metodo_pago = 'Pendiente')
                )
            """
            cursor.execute(query_eliminar_pagos)

            # Eliminar de turnos
            query_eliminar_turnos = f"""
                DELETE FROM turnos
                WHERE id_turno IN (
                    SELECT t.id_turno
                    FROM turnos t
                    LEFT JOIN pagos p ON t.id_turno = p.id_turno
                    WHERE DATEADD(SECOND, DATEDIFF(SECOND, 0, t.hora), CAST(t.fecha AS DATETIME)) < {cutoff_date}
                    AND (p.metodo_pago IS NULL OR p.metodo_pago = 'Pendiente')
                )
            """
            cursor.execute(query_eliminar_turnos)

            # Actualizar turnos pagados cuya fecha ya pasó
            query_actualizar_turnos_realizados = """
                UPDATE turnos
                SET estado = 'Realizado'
                WHERE id_turno IN (
                    SELECT t.id_turno
                    FROM turnos t
                    JOIN pagos p ON t.id_turno = p.id_turno
                    WHERE t.id_cliente = ?
                    AND p.metodo_pago != 'Pendiente'
                    AND CAST(t.fecha AS DATETIME) < GETDATE()
                )
            """
            cursor.execute(query_actualizar_turnos_realizados, (current_user.id_cliente,))
            
            # Confirmar cambios
            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"Error en eliminación de reservas: {e}")
            return jsonify({'error': 'Error al procesar el historial de reservas.'}), 500

        # Consulta del historial actualizado
        query_historial = """
            SELECT 
                t.id_turno,
                t.fecha,
                t.hora,
                t.estado,
                p.metodo_pago,
                s.nombre AS servicio
            FROM turnos t
            JOIN pagos p ON t.id_turno = p.id_turno
            JOIN turno_servicio ts ON t.id_turno = ts.id_turno
            JOIN servicios s ON ts.id_servicio = s.id_servicio
            WHERE t.id_cliente = ?
            ORDER BY t.fecha DESC, t.hora DESC
        """
        cursor.execute(query_historial, (current_user.id_cliente,))
        reservas = cursor.fetchall()
        conn.close()

        # Formatear el historial para la respuesta JSON
        historial = []
        for reserva in reservas:
            pago_estado = 'Pagado' if reserva.metodo_pago.lower() != 'pendiente' else 'Pendiente'
            historial.append({
                'id_turno': reserva.id_turno,
                'fecha': reserva.fecha.strftime('%Y-%m-%d'),
                'hora': reserva.hora.strftime('%H:%M'),
                'estado': reserva.estado,
                'pago': pago_estado,
                'servicio': reserva.servicio
            })

        return jsonify({'historial': historial}), 200

    else:
        return jsonify({'error': 'Error de conexión a la base de datos.'}), 500

