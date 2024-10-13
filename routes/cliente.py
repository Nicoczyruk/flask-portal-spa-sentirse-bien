# routes/cliente.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from database import get_db_connection

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

            query = """
                SELECT s.nombre AS servicio, t.fecha, t.hora, t.estado
                FROM turnos t
                INNER JOIN turno_servicio ts ON t.id_turno = ts.id_turno
                INNER JOIN servicios s ON ts.id_servicio = s.id_servicio
                WHERE t.id_cliente = ?
                ORDER BY t.fecha DESC, t.hora DESC
            """
            cursor.execute(query, (id_cliente,))
            results = cursor.fetchall()
            conn.close()
            reservas = []
            for row in results:
                reservas.append({
                    'servicio': row.servicio,
                    'fecha': row.fecha.strftime('%Y-%m-%d'),
                    'hora': str(row.hora),
                    'estado': row.estado
                })
            return jsonify({'reservas': reservas}), 200
        except Exception as e:
            conn.close()
            return jsonify({'error': 'Error al obtener las reservas'}), 500
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500

