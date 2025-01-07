import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from datetime import datetime
import markdown

# Configuración
DATABASE_FILE = "usuarios.db"
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Usa una variable de entorno para el token
print(f"Retrieved token: {TOKEN}")
RUTA_INFORMES = "Informe Final"
ultima_modificacion_guardada = {}
MAX_REINTENTOS_15M = 8
INTERVALO_REINTENTO_15M = 15  # Intervalo en segundos

# Configuración de logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear la base de datos si no existe
def inicializar_bd():
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                telegram_id TEXT UNIQUE
            )
        """)
        conn.commit()

# Comando /start
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    mensaje = f"Hola {user.first_name}, bienvenido al bot. Usa los comandos disponibles para interactuar."
    update.message.reply_text(mensaje)

# Comando /registrar_usuario
def registrar_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO usuarios (nombre, telegram_id) VALUES (?, ?)",
                (user.first_name, user.id)
            )
            conn.commit()
        update.message.reply_text("Usuario registrado exitosamente.")
    except Exception as e:
        logger.error(f"Error registrando usuario: {e}")
        update.message.reply_text("Ocurrió un error al registrar el usuario.")

# Función para revisar informes cada 15 minutos
def revisar_informe_15m(context: ContextTypes.DEFAULT_TYPE):
    try:
        reintentos = context.job.data.get("reintentos", 0)
        if reintentos >= MAX_REINTENTOS_15M:
            logger.warning("Máximo número de reintentos alcanzado para la tarea de revisión.")
            return

        # Verificar si el informe se ha modificado
        archivo = f"{RUTA_INFORMES}/reporte_15m.txt"
        if not os.path.exists(archivo):
            logger.warning("El archivo del informe no existe.")
            return

        ultima_modificacion = os.path.getmtime(archivo)
        if archivo not in ultima_modificacion_guardada or ultima_modificacion_guardada[archivo] != ultima_modificacion:
            ultima_modificacion_guardada[archivo] = ultima_modificacion
            with open(archivo, "r") as f:
                contenido = f.read()
            mensaje = f"Informe actualizado:\n{contenido}"
            context.bot.send_message(chat_id=context.job.chat_id, text=mensaje)
        else:
            logger.info("No hay cambios en el informe.")

    except Exception as e:
        context.job.data["reintentos"] = context.job.data.get("reintentos", 0) + 1
        logger.error(f"Error en la tarea de revisión: {e}")

# Comando para iniciar la tarea de revisión periódica
def iniciar_revision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.job_queue.run_repeating(
        revisar_informe_15m,
        interval=INTERVALO_REINTENTO_15M,
        first=0,
        chat_id=chat_id,
        name=str(chat_id),
        data={"reintentos": 0}
    )
    update.message.reply_text("La revisión periódica de informes ha comenzado.")

# Manejo de botones interactivos
def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()
    opcion = query.data
    if opcion == "opcion_1":
        query.edit_message_text("Elegiste la Opción 1.")
    elif opcion == "opcion_2":
        query.edit_message_text("Elegiste la Opción 2.")
    else:
        query.edit_message_text("Opción no reconocida.")

# Comando /menu para mostrar botones interactivos
def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    botones = [
        [InlineKeyboardButton("Opción 1", callback_data="opcion_1")],
        [InlineKeyboardButton("Opción 2", callback_data="opcion_2")]
    ]
    reply_markup = InlineKeyboardMarkup(botones)
    update.message.reply_text("Elige una opción:", reply_markup=reply_markup)

# Función principal para ejecutar el bot
def main():
    inicializar_bd()

    application = Application.builder().token(TOKEN).build()

    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("registrar_usuario", registrar_usuario))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("iniciar_revision", iniciar_revision))

    # Callbacks
    application.add_handler(CallbackQueryHandler(button))

    # Ejecutar el bot
    application.run_polling()

if __name__ == "__main__":
    main()
