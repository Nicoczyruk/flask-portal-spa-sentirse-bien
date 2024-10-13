# models.py

from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id_usuario, email):
        self.id = id_usuario
        self.email = email

    # Implementa métodos adicionales si es necesario
