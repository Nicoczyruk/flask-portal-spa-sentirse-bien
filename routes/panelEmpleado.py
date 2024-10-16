# routes/panelEmpleado.py

from flask import Blueprint, jsonify
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
