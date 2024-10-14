# models.py

from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id_usuario, email, rol, id_cliente=None):
        self.id = id_usuario
        self.email = email
        self.rol = rol
        self.id_cliente = id_cliente
    # Implementa métodos adicionales si es necesario
