# app.py

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager
import os
from models import User
from database import get_db_connection
# Importar blueprints
from routes.auth import auth_bp
from routes.cliente import cliente_bp
from routes.admin import admin_bp
from routes.reservas import reservas_bp
from routes.informes import informes_bp
from routes.panelEmpleado import panel_empleado_bp
from routes.panelprofesional import panel_profesional_bp

from config import Config  # Importar la configuración

app = Flask(__name__, static_folder='static')

# Configurar la clave secreta desde config.py
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Configurar Flask-CORS para permitir credenciales
CORS(app, supports_credentials=True)

# Configurar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth_bp.login'  # Ruta para redirigir si no está autenticado

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = "SELECT id_usuario, email, rol, id_cliente FROM usuarios WHERE id_usuario = ?"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            print("Usuario cargado con rol:", result.rol)  # Verifica si el rol se está obteniendo correctamente
            return User(id_usuario=result.id_usuario, email=result.email, rol=result.rol, id_cliente=result.id_cliente)
    return None

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(cliente_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(reservas_bp)
app.register_blueprint(informes_bp)
app.register_blueprint(panel_empleado_bp)
app.register_blueprint(panel_profesional_bp)

# Rutas para servir el frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    if path != '' and os.path.exists(os.path.join(app.static_folder, path)):
        # Si el archivo existe, se sirve directamente
        return send_from_directory(app.static_folder, path)
    else:
        # De lo contrario, se sirve index.html
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True)
