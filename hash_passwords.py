import bcrypt
from database import get_db_connection

def hash_passwords():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Obtener todos los usuarios y sus contraseñas actuales
            cursor.execute("SELECT id_usuario, password FROM usuarios")
            users = cursor.fetchall()

            for user in users:
                user_id = user.id_usuario
                plain_password = user.password

                # Hashear la contraseña
                hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())

                # Actualizar la contraseña en la base de datos
                update_query = "UPDATE usuarios SET password = ? WHERE id_usuario = ?"
                cursor.execute(update_query, (hashed_password.decode('utf-8'), user_id))

            # Confirmar los cambios
            conn.commit()
            print("Contraseñas hasheadas y actualizadas correctamente.")
        except Exception as e:
            print(f"Error al hashear las contraseñas: {e}")
            conn.rollback()
        finally:
            conn.close()
    else:
        print("No se pudo conectar a la base de datos.")

if __name__ == "__main__":
    hash_passwords()
