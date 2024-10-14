# routes/auth.py

from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from database import get_db_connection
import bcrypt

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

# routes/auth.py
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = "SELECT id_usuario, email, password, rol, id_cliente FROM usuarios WHERE email = ?"
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        conn.close()

        if result:
            stored_password_hash = result.password
            user_id = result.id_usuario
            rol = result.rol
            id_cliente = result.id_cliente  # Obtener id_cliente
            print("Rol del usuario durante login:", rol)  # Verifica si el rol es 'admin' o 'Cliente'

            if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8')):
                user = User(id_usuario=user_id, email=email, rol=rol, id_cliente=id_cliente)
                login_user(user)

                return jsonify({'message': 'Inicio de sesión exitoso'}), 200
            else:
                return jsonify({'error': 'Credenciales inválidas'}), 401
        else:
            return jsonify({'error': 'Credenciales inválidas'}), 401
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Sesión cerrada exitosamente'}), 200

@auth_bp.route('/status', methods=['GET'])
def auth_status():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True}), 200
    else:
        return jsonify({'authenticated': False}), 401

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    nombre = data.get('nombre')
    apellido = data.get('apellido')
    email = data.get('email')
    telefono = data.get('telefono')
    direccion = data.get('direccion')
    nombre_usuario = data.get('nombre_usuario')
    password = data.get('password')
    rol = data.get('rol', 'Cliente')  # Predeterminado a Cliente

    # Validar campos requeridos
    if not all([nombre, apellido, email, nombre_usuario, password]):
        return jsonify({'error': 'Faltan campos requeridos'}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Verificar si el email o nombre_usuario ya existen
            cursor.execute("SELECT * FROM usuarios WHERE email = ? OR nombre_usuario = ?", (email, nombre_usuario))
            existing_user = cursor.fetchone()
            if existing_user:
                return jsonify({'error': 'El email o nombre de usuario ya están en uso'}), 400

            # Insertar en clientes y obtener id_cliente usando OUTPUT
            cursor.execute("""
                INSERT INTO [dbo].[clientes] (nombre, apellido, email, telefono, direccion)
                OUTPUT INSERTED.id_cliente
                VALUES (?, ?, ?, ?, ?)
            """, (nombre, apellido, email, telefono, direccion))
            id_cliente = cursor.fetchone()[0]

            if not id_cliente:
                raise Exception("No se pudo obtener id_cliente.")

            # Hashear la contraseña
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Insertar en usuarios
            cursor.execute("""
                INSERT INTO [dbo].[usuarios] (id_cliente, nombre_usuario, password, email, rol)
                VALUES (?, ?, ?, ?, ?)
            """, (id_cliente, nombre_usuario, hashed_password, email, rol))
            conn.commit()

            return jsonify({"message": "Usuario registrado exitosamente"}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({'error': 'Error en el registro', 'details': str(e)}), 500
        finally:
            conn.close()
    else:
        return jsonify({'error': 'Error al conectar con la base de datos'}), 500


# routes/auth.py

@auth_bp.route('/current-user', methods=['GET'])
@login_required
def current_user_info():
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'rol': current_user.rol
    }), 200

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    if not current_user.is_authenticated:
        return jsonify({'error': 'No autenticado.'}), 401

    user_data = {
        'id_usuario': current_user.id,
        'email': current_user.email,
        'rol': current_user.rol,
        'id_cliente': current_user.id_cliente
    }

    return jsonify({'user': user_data}), 200