# routes/panelEmpleado.py

from flask import Blueprint, jsonify, request
from flask_login import login_required
from database import get_db_connection
from datetime import datetime

panel_empleado_bp = Blueprint('panel_empleado_bp', __name__, url_prefix='/api/empleado')

@panel_empleado_bp.route('/pagos-dia', methods=['GET'])
@login_required
def pagos_del_dia():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            fecha_actual = datetime.now().date()
            query = """
                SELECT p.id_pago, p.monto, p.metodo_pago, p.fecha_pago, 
                       c.nombre AS cliente, c.apellido AS cliente_apellido
                FROM pagos p
                JOIN turnos t ON p.id_turno = t.id_turno
                JOIN clientes c ON t.id_cliente = c.id_cliente
                WHERE CAST(p.fecha_pago AS DATE) = ? 
                AND p.metodo_pago != 'Pendiente'
                ORDER BY p.fecha_pago ASC
            """
            cursor.execute(query, (fecha_actual,))
            pagos = cursor.fetchall()
            
            pagos_list = [
                {
                    "id_pago": pago[0],
                    "monto": float(pago[1]),
                    "metodo_pago": pago[2],
                    "fecha_pago": pago[3].strftime('%Y-%m-%d %H:%M:%S'),
                    "cliente": f"{pago[4]} {pago[5]}"
                }
                for pago in pagos
            ]

            total_ingresos = sum(pago['monto'] for pago in pagos_list)
            return jsonify({"pagos": pagos_list, "total_ingresos": total_ingresos}), 200
        except Exception as e:
            print(f"Error en pagos_del_dia: {e}")
            return jsonify({"error": "Error al obtener los pagos del día."}), 500
        finally:
            conn.close()
    return jsonify({"error": "Error de conexión a la base de datos."}), 500

@panel_empleado_bp.route('/profesionales', methods=['GET'])
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

@panel_empleado_bp.route('/clientes-profesional', methods=['GET'])
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