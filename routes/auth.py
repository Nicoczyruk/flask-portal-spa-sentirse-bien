# routes/auth.py

from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from database import get_db_connection
import bcrypt

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Validar que los campos no estén vacíos
    if not email or not password:
        return jsonify({'error': 'Faltan datos de correo electrónico o contraseña'}), 400

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # Consulta para obtener el hash de la contraseña del usuario basado en el email
        query = "SELECT id_usuario, email, password FROM usuarios WHERE email = ?"
        cursor.execute(query, (email,))
        result = cursor.fetchone()
        conn.close()

        if result:
            stored_password_hash = result.password  # Accedemos a la columna 'password'
            user_id = result.id_usuario

            # Verificar la contraseña usando bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8')):
                # Contraseña correcta, crear objeto User
                user = User(id_usuario=user_id, email=email)
                login_user(user)  # Iniciar sesión del usuario

                return jsonify({'message': 'Inicio de sesión exitoso'}), 200
            else:
                # Contraseña incorrecta
                return jsonify({'error': 'Credenciales inválidas'}), 401
        else:
            # Usuario no encontrado
            return jsonify({'error': 'Credenciales inválidas'}), 401
    else:
        return jsonify({'error': 'Error al conectar a la base de datos'}), 500

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
