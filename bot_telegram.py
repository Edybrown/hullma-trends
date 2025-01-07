import os
import logging
import sqlite3
import markdown
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
import asyncio
import time

# Configuracion
DATABASE_FILE = "usuarios.db"
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("La variable de entorno TELEGRAM_TOKEN no está definida.")
RUTA_INFORMES = "Informe Final"
ultima_modificacion_guardada = {}
MAX_REINTENTOS_15M = 3
INTERVALO_REINTENTO_15M = 15

# Configuracion de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Función para enviar informes
async def enviar_informe(context: ContextTypes.DEFAULT_TYPE, nombre_archivo):
    bot = context.bot
    ruta_archivo = os.path.join(RUTA_INFORMES, nombre_archivo)
    if os.path.exists(ruta_archivo):
        try:
            with open(ruta_archivo, "r", encoding="utf-8") as archivo:
                contenido_informe = archivo.read()
                html = markdown.markdown(contenido_informe)
                usuarios = obtener_todos_usuarios()
                for usuario in usuarios:
                    try:
                        await bot.send_message(chat_id=usuario[0], text=html, parse_mode=ParseMode.HTML)
                        logger.info(f"Informe {nombre_archivo} enviado a {usuario[0]}")
                    except telegram.error.TelegramError as e:
                        logger.error(f"Error al enviar mensaje a {usuario[0]}: {e}")
        except FileNotFoundError:
            logger.error(f"Archivo no encontrado: {ruta_archivo}")
        except Exception as e:
            logger.error(f"Error al procesar {ruta_archivo}: {e}")

# Función para obtener todos los usuarios
def obtener_todos_usuarios():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM usuarios")
        usuarios = cursor.fetchall()
        return usuarios
    except sqlite3.Error as e:
        logger.error(f"Error al obtener usuarios: {e}")
        return []
    finally:
        conn.close()

async def revisar_informe(context: ContextTypes.DEFAULT_TYPE, nombre_archivo):
    ruta_archivo = os.path.join(RUTA_INFORMES, nombre_archivo)
    if not os.path.exists(ruta_archivo):
        return

    ultima_modificacion = os.path.getmtime(ruta_archivo)

    if ultima_modificacion > ultima_modificacion_guardada.get(nombre_archivo, 0):
        ultima_modificacion_guardada[nombre_archivo] = ultima_modificacion
        await enviar_informe(context, nombre_archivo)
        context.job.data["reintentos"][nombre_archivo] = 0  # Reiniciar contador
    elif context.job.data["reintentos"].get(nombre_archivo, 0) < MAX_REINTENTOS_15M:
        context.job.data["reintentos"][nombre_archivo] = context.job.data["reintentos"].get(nombre_archivo, 0) + 1
        logger.info(f"Reintento {context.job.data['reintentos'][nombre_archivo]} para {nombre_archivo}")
    else:
        logger.info(f"Máximo de reintentos alcanzado para {nombre_archivo}.")
        context.job.data["reintentos"][nombre_archivo] = 0  # Reiniciar contador

async def revisar_informes(context: ContextTypes.DEFAULT_TYPE):
    archivos_informes = ["report_15m.md", "report_1h.md", "report_4h.md", "report_1d.md"]
    for archivo in archivos_informes:
        await revisar_informe(context, archivo)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Bienvenido al bot de informes.")

async def setup_bot():
    application = Application.builder().token(TOKEN).build()
    
    # Agregar manejadores
    application.add_handler(CommandHandler("start", start))
    
    # Configurar trabajos periódicos
    job_queue = application.job_queue
    job_queue.run_repeating(revisar_informes, interval=900, first=10, data={"reintentos": {}})

    return application

async def main():
    try:
        application = await setup_bot()
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        await application.updater.idle()
    except Exception as e:
        logger.exception(f"Error inesperado en main: {e}")
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
