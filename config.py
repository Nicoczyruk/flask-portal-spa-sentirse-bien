# config.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Config:
    # Leer la cadena de conexión desde la variable de entorno o usar una por defecto
    CONNECTION_STRING = os.getenv('DATABASE_CONNECTION_STRING', (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=spa-sentirse-bien;"
        "Trusted_Connection=yes;"
        "Encrypt=no;"
    ))
    
    # Clave secreta para Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave_por_defecto')
