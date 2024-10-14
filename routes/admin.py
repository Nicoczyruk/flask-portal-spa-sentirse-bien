from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from database import get_db_connection

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/api/admin')


@admin_bp.route('/clientes', methods=['GET'])
@login_required
def listar_clientes():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id_cliente, nombre, apellido, email, telefono, direccion, fecha_registro FROM clientes")
        clientes = cursor.fetchall()
        clientes_list = [dict(zip([column[0] for column in cursor.description], row)) for row in clientes]
        conn.close()
        return jsonify(clientes_list), 200
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


@admin_bp.route('/clientes-dia', methods=['GET'])
@login_required
def clientes_por_dia():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = """
            SELECT t.fecha, t.hora, s.nombre AS servicio, c.nombre, c.apellido
            FROM turnos t
            JOIN turno_servicio ts ON t.id_turno = ts.id_turno
            JOIN servicios s ON ts.id_servicio = s.id_servicio
            JOIN clientes c ON t.id_cliente = c.id_cliente
            ORDER BY t.fecha, t.hora
        """
        cursor.execute(query)
        registros = cursor.fetchall()
        registros_list = []
        
        for row in registros:
            registro_dict = dict(zip([column[0] for column in cursor.description], row))
            # Convertir 'fecha' y 'hora' a formatos serializables
            registro_dict['fecha'] = registro_dict['fecha'].strftime('%Y-%m-%d')
            registro_dict['hora'] = registro_dict['hora'].strftime('%H:%M')  # Aquí se serializa el objeto 'time'
            registros_list.append(registro_dict)
        
        conn.close()
        return jsonify(registros_list), 200
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


@admin_bp.route('/clientes-profesional', methods=['GET'])
@login_required
def clientes_por_profesional():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = """
            SELECT p.nombre AS profesional, t.fecha, t.hora, c.nombre, c.apellido
            FROM turnos t
            JOIN profesionales p ON t.id_profesional = p.id_profesional
            JOIN clientes c ON t.id_cliente = c.id_cliente
            ORDER BY p.nombre, t.fecha, t.hora
        """
        cursor.execute(query)
        registros = cursor.fetchall()
        registros_list = []
        
        for row in registros:
            registro_dict = dict(zip([column[0] for column in cursor.description], row))
            # Convertir 'fecha' y 'hora' a formatos serializables
            registro_dict['fecha'] = registro_dict['fecha'].strftime('%Y-%m-%d')
            registro_dict['hora'] = registro_dict['hora'].strftime('%H:%M')  # Aquí se serializa el objeto 'time'
            registros_list.append(registro_dict)
        
        conn.close()
        return jsonify(registros_list), 200
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500
