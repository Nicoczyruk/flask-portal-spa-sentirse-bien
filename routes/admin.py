# routes/Admin.py

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from database import get_db_connection
from datetime import datetime
import bcrypt  

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/api/admin')


@admin_bp.route('/clientes', methods=['GET'])
@login_required
def listar_clientes():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id_cliente, nombre, apellido, email, telefono, direccion, fecha_registro
            FROM clientes
            ORDER BY id_cliente ASC
        """)
        clientes = cursor.fetchall()
        clientes_list = [dict(zip([column[0] for column in cursor.description], row)) for row in clientes]
        conn.close()
        return jsonify(clientes_list), 200
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


@admin_bp.route('/profesionales', methods=['GET'])
@login_required
def listar_profesionales():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id_profesional, nombre, apellido FROM profesionales ORDER BY nombre ASC")
        profesionales = cursor.fetchall()
        profesionales_list = [dict(zip([column[0] for column in cursor.description], row)) for row in profesionales]
        conn.close()
        return jsonify(profesionales_list), 200
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


@admin_bp.route('/clientes-dia', methods=['GET'])
@login_required
def clientes_por_dia():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener la fecha desde los parámetros o usar la fecha actual
            fecha_str = request.args.get('fecha')
            if fecha_str:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            else:
                fecha = datetime.now().date()
            
            query = """
                SELECT t.fecha, t.hora, s.nombre AS servicio, c.nombre, c.apellido
                FROM turnos t
                JOIN turno_servicio ts ON t.id_turno = ts.id_turno
                JOIN servicios s ON ts.id_servicio = s.id_servicio
                JOIN clientes c ON t.id_cliente = c.id_cliente
                JOIN pagos p ON p.id_turno = t.id_turno
                WHERE t.fecha = ? AND p.metodo_pago != 'Pendiente'
                ORDER BY t.hora ASC
            """
            cursor.execute(query, (fecha,))
            registros = cursor.fetchall()
            registros_list = []
            
            for row in registros:
                registro_dict = dict(zip([column[0] for column in cursor.description], row))
                # Convertir 'fecha' y 'hora' a formatos serializables
                registro_dict['fecha'] = registro_dict['fecha'].strftime('%Y-%m-%d')
                registro_dict['hora'] = registro_dict['hora'].strftime('%H:%M')
                registros_list.append(registro_dict)
            
            conn.close()
            return jsonify(registros_list), 200
        except Exception as e:
            conn.close()
            print(f"Error en clientes_por_dia: {e}")  # Para depuración
            return jsonify({'error': 'Error al obtener los clientes del día'}), 500
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


@admin_bp.route('/clientes-profesional', methods=['GET'])
@login_required
def clientes_por_profesional():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener los parámetros 'profesional_id' y 'fecha'
            profesional_id = request.args.get('profesional_id')
            fecha_str = request.args.get('fecha')
            if not profesional_id or not fecha_str:
                return jsonify({'error': 'Parámetros profesional_id y fecha son requeridos.'}), 400
            
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            
            # Verificar que el profesional exista
            cursor.execute("SELECT COUNT(*) FROM profesionales WHERE id_profesional = ?", (profesional_id,))
            exists = cursor.fetchone()[0]
            if not exists:
                return jsonify({'error': 'Profesional no encontrado.'}), 404

            query = """
                SELECT p.nombre AS profesional, t.fecha, t.hora, c.nombre, c.apellido
                FROM turnos t
                JOIN profesionales p ON t.id_profesional = p.id_profesional
                JOIN clientes c ON t.id_cliente = c.id_cliente
                JOIN pagos pmt ON pmt.id_turno = t.id_turno
                WHERE p.id_profesional = ? AND t.fecha = ? AND pmt.metodo_pago != 'Pendiente'
                ORDER BY t.hora ASC
            """
            cursor.execute(query, (profesional_id, fecha,))
            registros = cursor.fetchall()
            registros_list = []
            
            for row in registros:
                registro_dict = dict(zip([column[0] for column in cursor.description], row))
                # Convertir 'fecha' y 'hora' a formatos serializables
                registro_dict['fecha'] = registro_dict['fecha'].strftime('%Y-%m-%d')
                registro_dict['hora'] = registro_dict['hora'].strftime('%H:%M')
                registros_list.append(registro_dict)
            
            conn.close()
            return jsonify(registros_list), 200
        except Exception as e:
            conn.close()
            print(f"Error en clientes_por_profesional: {e}")  # Para depuración
            return jsonify({'error': 'Error al obtener los clientes por profesional'}), 500
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


# Nuevas rutas para agregar y eliminar profesionales y empleados

@admin_bp.route('/add-profesional', methods=['POST'])
@login_required
def add_profesional():
    data = request.get_json()
    required_fields = ['nombre', 'apellido', 'especialidad', 'email', 'telefono', 'nombre_usuario', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Faltan campos requeridos.'}), 400
    
    nombre = data['nombre']
    apellido = data['apellido']
    especialidad = data['especialidad']
    email = data['email']
    telefono = data['telefono']
    nombre_usuario = data['nombre_usuario']
    password = data['password']
    
    # Hashear la contraseña
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Insertar en profesionales
            cursor.execute("""
                INSERT INTO profesionales (nombre, apellido, especialidad, email, telefono)
                VALUES (?, ?, ?, ?, ?)
            """, (nombre, apellido, especialidad, email, telefono))
            
            # Obtener el último id_profesional insertado
            cursor.execute("SELECT SCOPE_IDENTITY()")
            id_profesional = cursor.fetchone()[0]
            
            # Insertar en usuarios con id_cliente NULL y rol 'Profesional'
            cursor.execute("""
                INSERT INTO usuarios (id_cliente, nombre_usuario, password, email, rol)
                VALUES (NULL, ?, ?, ?, 'Profesional')
            """, (nombre_usuario, hashed_password, email))
            
            conn.commit()
            conn.close()
            return jsonify({'message': 'Profesional y usuario creados exitosamente.'}), 201
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error en add_profesional: {e}")
            return jsonify({'error': 'Error al agregar el profesional.'}), 500
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


@admin_bp.route('/remove-profesional', methods=['DELETE'])
@login_required
def remove_profesional():
    data = request.get_json()
    if 'id_profesional' not in data:
        return jsonify({'error': 'id_profesional es requerido.'}), 400
    
    id_profesional = data['id_profesional']
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener el email del profesional para eliminar el usuario asociado
            cursor.execute("SELECT email FROM profesionales WHERE id_profesional = ?", (id_profesional,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return jsonify({'error': 'Profesional no encontrado.'}), 404
            email = result[0]
            
            # Eliminar de profesionales
            cursor.execute("DELETE FROM profesionales WHERE id_profesional = ?", (id_profesional,))
            
            # Eliminar de usuarios
            cursor.execute("DELETE FROM usuarios WHERE email = ? AND rol = 'Profesional'", (email,))
            
            conn.commit()
            conn.close()
            return jsonify({'message': 'Profesional y usuario eliminados exitosamente.'}), 200
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error en remove_profesional: {e}")
            return jsonify({'error': 'Error al eliminar el profesional.'}), 500
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


@admin_bp.route('/add-empleado', methods=['POST'])
@login_required
def add_empleado():
    data = request.get_json()
    required_fields = ['nombre', 'apellido', 'email', 'telefono', 'direccion', 'nombre_usuario', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Faltan campos requeridos.'}), 400
    
    nombre = data['nombre']
    apellido = data['apellido']
    email = data['email']
    telefono = data['telefono']
    direccion = data['direccion']
    nombre_usuario = data['nombre_usuario']
    password = data['password']
    
    # Hashear la contraseña
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Insertar en la tabla clientes y obtener el id_cliente con OUTPUT
            cursor.execute("""
                INSERT INTO clientes (nombre, apellido, email, telefono, direccion)
                OUTPUT INSERTED.id_cliente
                VALUES (?, ?, ?, ?, ?)
            """, (nombre, apellido, email, telefono, direccion))
            
            # Obtener el id_cliente insertado
            id_cliente = cursor.fetchone()[0]
    
            # Insertar en la tabla usuarios con el id_cliente obtenido y el rol 'Empleado'
            cursor.execute("""
                INSERT INTO usuarios (id_cliente, nombre_usuario, password, email, rol)
                VALUES (?, ?, ?, ?, 'Empleado')
            """, (id_cliente, nombre_usuario, hashed_password, email))
            
            conn.commit()
            conn.close()
            return jsonify({'message': 'Empleado y usuario creados exitosamente.'}), 201
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error en add_empleado: {e}")
            return jsonify({'error': 'Error al agregar el empleado.'}), 500
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500


@admin_bp.route('/remove-empleado', methods=['DELETE'])
@login_required
def remove_empleado():
    data = request.get_json()
    if 'id_empleado' not in data:
        return jsonify({'error': 'id_empleado es requerido.'}), 400
    
    id_empleado = data['id_empleado']
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener el email del empleado para eliminar el usuario asociado
            cursor.execute("SELECT email FROM clientes WHERE id_cliente = ?", (id_empleado,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return jsonify({'error': 'Empleado no encontrado.'}), 404
            email = result[0]
            
            # Eliminar de usuarios
            cursor.execute("DELETE FROM usuarios WHERE id_cliente = ? AND rol = 'Empleado'", (id_empleado,))
            
            # Eliminar de clientes
            cursor.execute("DELETE FROM clientes WHERE id_cliente = ?", (id_empleado,))
            
            conn.commit()
            conn.close()
            return jsonify({'message': 'Empleado y usuario eliminados exitosamente.'}), 200
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error en remove_empleado: {e}")
            return jsonify({'error': 'Error al eliminar el empleado.'}), 500
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500

@admin_bp.route('/empleados', methods=['GET'])
@login_required
def listar_empleados():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id_cliente, c.nombre, c.apellido
            FROM clientes c
            JOIN usuarios u ON c.id_cliente = u.id_cliente
            WHERE u.rol = 'Empleado'
            ORDER BY c.nombre ASC
        """)
        empleados = cursor.fetchall()
        empleados_list = [dict(zip([column[0] for column in cursor.description], row)) for row in empleados]
        conn.close()
        return jsonify(empleados_list), 200
    return jsonify({'error': 'Error de conexión a la base de datos'}), 500
