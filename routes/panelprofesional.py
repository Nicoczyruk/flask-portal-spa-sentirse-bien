# routes/panelprofesional.py

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from database import get_db_connection
from datetime import datetime

panel_profesional_bp = Blueprint('panel_profesional_bp', __name__, url_prefix='/api/profesional')

@panel_profesional_bp.route('/turnos', methods=['GET'])
@login_required
def obtener_turnos_profesional():
    try:
        # Obtener el correo electrónico del usuario actual
        email_usuario = current_user.email
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener el id_profesional basado en el email
        cursor.execute("SELECT id_profesional FROM profesionales WHERE email = ?", (email_usuario,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'error': 'Profesional no encontrado.'}), 404
        
        profesional_id = result[0]
        
        # Obtener la fecha desde los parámetros o usar la fecha actual
        fecha_str = request.args.get('fecha', datetime.today().strftime('%Y-%m-%d'))
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()

        query = """
            SELECT t.fecha, t.hora, s.nombre AS servicio, c.nombre, c.apellido
            FROM turnos t
            JOIN clientes c ON t.id_cliente = c.id_cliente
            JOIN turno_servicio ts ON t.id_turno = ts.id_turno
            JOIN servicios s ON ts.id_servicio = s.id_servicio
            WHERE t.id_profesional = ? AND t.fecha = ?
            ORDER BY t.hora ASC
        """
        cursor.execute(query, (profesional_id, fecha))
        turnos = cursor.fetchall()

        turnos_list = [
            {
                "fecha": turno[0].strftime('%Y-%m-%d'),
                "hora": turno[1].strftime('%H:%M:%S'),
                "servicio": turno[2],
                "cliente": f"{turno[3]} {turno[4]}"
            }
            for turno in turnos
        ]

        conn.close()
        return jsonify(turnos_list), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Error al obtener los turnos.'}), 500
