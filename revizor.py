import sqlite3
import os
import datetime

DATABASE_FILE = 'usuarios_telegram.db'  # Nombre de tu archivo de base de datos

def verificar_base_de_datos():
    """Verifica el contenido de la base de datos y muestra información relevante."""

    if not os.path.exists(DATABASE_FILE):
        print(f"[ERROR] El archivo de base de datos '{DATABASE_FILE}' no existe.")
        return

    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()

            # 1. Contar el número total de usuarios:
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            total_usuarios = cursor.fetchone()[0]
            print(f"\nNúmero total de usuarios: {total_usuarios}")

            # 2. Mostrar los últimos 10 usuarios registrados (o todos si hay menos de 10):
            cursor.execute("SELECT * FROM usuarios ORDER BY id DESC LIMIT 10")
            ultimos_usuarios = cursor.fetchall()

            if ultimos_usuarios:
                print("\nÚltimos usuarios registrados:")
                for usuario in ultimos_usuarios:
                    print(f"  ID: {usuario[0]}, Chat ID: {usuario[1]}, Nombre: {usuario[2]}, Suscripciones: {usuario[3]}, Fecha de Suscripción: {usuario[4]}, Última Actividad: {usuario[5]}")
            else:
                print("  No hay usuarios registrados.")

            # 3. Mostrar información sobre un chat_id específico (si lo necesitas):
            chat_id_a_verificar = input("\nIntroduce un Chat ID para verificar (o presiona Enter para omitir): ")
            if chat_id_a_verificar:
                try:
                    chat_id_a_verificar = int(chat_id_a_verificar)
                    cursor.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id_a_verificar,))
                    usuario_especifico = cursor.fetchone()
                    if usuario_especifico:
                        print(f"\nInformación del usuario con Chat ID {chat_id_a_verificar}:")
                        print(f"  ID: {usuario_especifico[0]}, Chat ID: {usuario_especifico[1]}, Nombre: {usuario_especifico[2]}, Suscripciones: {usuario_especifico[3]}, Fecha de Suscripción: {usuario_especifico[4]}, Última Actividad: {usuario_especifico[5]}")
                    else:
                        print(f"  No se encontró ningún usuario con el Chat ID {chat_id_a_verificar}.")
                except ValueError:
                    print("Chat ID inválido. Debe ser un número entero.")

            # 4. Verificar si hay fechas inválidas (opcional, pero útil para depuración):
            cursor.execute("SELECT id, suscripcion_fecha FROM usuarios WHERE suscripcion_fecha IS NULL")
            fechas_invalidas = cursor.fetchall()
            if fechas_invalidas:
                print("\n¡ATENCIÓN! Se encontraron fechas de suscripción inválidas (NULL):")
                for id_usuario, fecha in fechas_invalidas:
                    print(f"  ID del usuario: {id_usuario}")

    except sqlite3.Error as e:
        print(f"[ERROR] Error al acceder a la base de datos: {e}")

if __name__ == "__main__":
    verificar_base_de_datos()
