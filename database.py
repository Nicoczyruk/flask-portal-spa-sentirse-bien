# database.py
import pyodbc
from config import Config

def get_db_connection():
    try:
        conn = pyodbc.connect(Config.CONNECTION_STRING)
        print("Conexión exitosa a la base de datos.")
        return conn
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION;")
        row = cursor.fetchone()
        print(f"Versión de SQL Server: {row[0]}")
        conn.close()
