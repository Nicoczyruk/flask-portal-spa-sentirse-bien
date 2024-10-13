# routes/protected.py

from flask import Blueprint, jsonify
from flask_login import login_required, current_user

protected_bp = Blueprint('protected_bp', __name__, url_prefix='/api')

@protected_bp.route('/protected-data', methods=['GET'])
@login_required
def protected_data():
    return jsonify({'data': 'Este es un dato protegido', 'user': current_user.email}), 200
