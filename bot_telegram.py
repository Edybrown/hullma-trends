import os
import logging
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

# Configuración del logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    logger.error("No se encontró el token del bot. Asegúrate de tener la variable de entorno TELEGRAM_TOKEN configurada.")
    exit(1)

# Nombre de la base de datos
DATABASE_FILE = "documentos.db"

# Función de inicialización de la base de datos
def init_db():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documentos (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                fecha_vencimiento TEXT NOT NULL
            )
        """)
        conn.commit()
        logger.info("Base de datos inicializada o verificada.")
    except sqlite3.Error as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
    finally:
        if conn:
            conn.close()

# Funciones de base de datos (con manejo de excepciones y contextos)
def agregar_documento(nombre, fecha_vencimiento):
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO documentos (nombre, fecha_vencimiento) VALUES (?, ?)", (nombre, fecha_vencimiento))
            conn.commit()
            logger.info(f"Documento '{nombre}' agregado.")
    except sqlite3.Error as e:
        logger.error(f"Error al agregar documento: {e}")

def obtener_documentos():
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documentos")
            return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Error al obtener documentos: {e}")
        return []

def eliminar_documento(documento_id):
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documentos WHERE id = ?", (documento_id,))
            conn.commit()
            logger.info(f"Documento con ID {documento_id} eliminado.")
    except sqlite3.Error as e:
        logger.error(f"Error al eliminar documento: {e}")

# Función de cálculo de tiempo restante
def calcular_dias_restantes(fecha_vencimiento):
    try:
        hoy = datetime.now().date()
        vencimiento = datetime.strptime(fecha_vencimiento, "%Y-%m-%d").date()
        return (vencimiento - hoy).days
    except ValueError:
        logger.error(f"Formato de fecha incorrecto: {fecha_vencimiento}. Se esperaba YYYY-MM-DD")
        return None  # Devuelve None en caso de error

# Funciones para manejar comandos de Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    botones = [
        [InlineKeyboardButton("Agregar Documento", callback_data="agregar_documento")],
        [InlineKeyboardButton("Revisar Documentos", callback_data="revisar_documentos")],
    ]
    reply_markup = InlineKeyboardMarkup(botones)
    await update.message.reply_text("Bienvenido al bot de gestión de documentos. ¿Qué deseas hacer?", reply_markup=reply_markup)
    context.user_data.clear() #Limpiar data al iniciar

async def boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "agregar_documento":
        await query.edit_message_text("Por favor, envía el nombre del documento y la fecha de vencimiento en el formato: `nombre,AAAA-MM-DD`")
        context.user_data["accion"] = "agregar_documento"
    elif query.data == "revisar_documentos":
        documentos = obtener_documentos()
        if not documentos:
            await query.edit_message_text("No hay documentos registrados.")
        else:
            mensaje = "Documentos registrados:\n"
            for doc in documentos:
                dias_restantes = calcular_dias_restantes(doc[2])
                if dias_restantes is not None: #Manejo de error de fecha
                    mensaje += f"- {doc[1]} (Vence en {dias_restantes} días)\n"
                else:
                    mensaje += f"- {doc[1]} (Fecha con formato incorrecto)\n"
            await query.edit_message_text(mensaje)

async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "accion" in context.user_data and context.user_data["accion"] == "agregar_documento":
        try:
            nombre, fecha_vencimiento = update.message.text.split(", ")
            agregar_documento(nombre, fecha_vencimiento)
            await update.message.reply_text("Documento agregado exitosamente.")
        except ValueError:
            await update.message.reply_text("Error en el formato. Por favor, usa `nombre,AAAA-MM-DD`.")
        finally:
            context.user_data.pop("accion", None) #Limpiar data despues de usarla
    else:
        await update.message.reply_text("No entiendo el mensaje. Usa /start para comenzar.")

# Configuración principal del bot
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(boton))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje)) #Manejador para mensajes de texto
    app.run_polling()

if __name__ == "__main__":
    main()
