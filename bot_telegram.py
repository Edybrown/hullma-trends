import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import requests
import json
import time
from apscheduler.schedulers.background import BackgroundScheduler

# Cargar las variables de entorno desde .env
load_dotenv()

# Configurar el logging para ver los mensajes de error
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Conectar a la base de datos SQLite
import sqlite3

def create_db():
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()

    # Crear la tabla de usuarios con las nuevas columnas
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY,
                    chat_id INTEGER UNIQUE,
                    nombre TEXT,
                    suscripciones TEXT,
                    suscripcion_fecha TIMESTAMP,
                    suscripcion_tipo TEXT,
                    fecha_ultima_actividad TIMESTAMP)''')
    
    conn.commit()
    conn.close()

def modify_db():
    """Esta función modificará la base de datos para agregar nuevas columnas si es necesario."""
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()

    # Agregar nuevas columnas si no existen
    try:
        c.execute('ALTER TABLE usuarios ADD COLUMN suscripcion_fecha TIMESTAMP')
    except sqlite3.OperationalError:
        pass  # Si ya existe, ignorar el error.

    try:
        c.execute('ALTER TABLE usuarios ADD COLUMN suscripcion_tipo TEXT')
    except sqlite3.OperationalError:
        pass  # Si ya existe, ignorar el error.

    try:
        c.execute('ALTER TABLE usuarios ADD COLUMN fecha_ultima_actividad TIMESTAMP')
    except sqlite3.OperationalError:
        pass  # Si ya existe, ignorar el error.

    conn.commit()
    conn.close()

# Llamar a las funciones para crear la base de datos y modificarla si es necesario
create_db()
modify_db()

# Guardar o actualizar los datos de los usuarios
def save_user(chat_id, nombre):
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO usuarios (chat_id, nombre, suscripciones) VALUES (?, ?, ?)",
              (chat_id, nombre, ''))
    conn.commit()
    conn.close()

# Obtener los usuarios y suscripciones
def get_users():
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()
    c.execute("SELECT chat_id, suscripciones FROM usuarios")
    users = c.fetchall()
    conn.close()
    return users

# Función para obtener el análisis de mercado (simulación)
def obtener_analisis():
    # Esto debería ser una consulta real de mercado, por ejemplo usando APIs como Phemex
    return {
        '15m': 'Análisis de 15m: El precio ha subido un 2%.',
        '1h': 'Análisis de 1h: El precio ha bajado un 1.5%.',
        '4h': 'Análisis de 4h: El precio se ha mantenido estable.',
        '1d': 'Análisis de 1d: El precio ha aumentado un 5%.'
    }

# Enviar los informes periódicos
def enviar_informes(application):
    analisis = obtener_analisis()

    # Obtener usuarios suscritos
    users = get_users()
    for user in users:
        chat_id, suscripciones = user
        suscripciones = suscripciones.split(',') if suscripciones else []

        # Enviar análisis solo a los usuarios suscritos a la temporalidad
        for temporalidad in suscripciones:
            if temporalidad in analisis:
                message = analisis[temporalidad]
                application.bot.send_message(chat_id, message)

# Comando de inicio para el bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    save_user(update.message.chat_id, user.first_name)

    welcome_message = "¡Hola! Soy un bot que te envía análisis de mercado en diferentes temporalidades.\n\n" \
                      "Para comenzar, usa los botones para suscribirte a las temporalidades que te interesen."
    keyboard = [
        [InlineKeyboardButton("Suscribirse a 15m", callback_data='suscribir_15m')],
        [InlineKeyboardButton("Suscribirse a 1h", callback_data='suscribir_1h')],
        [InlineKeyboardButton("Suscribirse a 4h", callback_data='suscribir_4h')],
        [InlineKeyboardButton("Suscribirse a 1d", callback_data='suscribir_1d')],
        [InlineKeyboardButton("Desuscribirse", callback_data='desuscribir')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# Función para manejar la suscripción y desuscripción
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data

    # Obtener usuario de la base de datos
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()
    c.execute("SELECT suscripciones FROM usuarios WHERE chat_id = ?", (chat_id,))
    suscripciones = c.fetchone()
    if suscripciones:
        suscripciones = suscripciones[0].split(',')
    else:
        suscripciones = []

    if data.startswith('suscribir'):
        temporalidad = data.split('_')[1]
        if temporalidad not in suscripciones:
            suscripciones.append(temporalidad)
            c.execute("UPDATE usuarios SET suscripciones = ? WHERE chat_id = ?",
                      (','.join(suscripciones), chat_id))
            conn.commit()
            await query.answer(f"Te has suscrito a {temporalidad}.")

    elif data == 'desuscribir':
        suscripciones = []
        c.execute("UPDATE usuarios SET suscripciones = ? WHERE chat_id = ?",
                  ('', chat_id))
        conn.commit()
        await query.answer("Te has desuscrito de todas las temporalidades.")

    conn.close()
    # Actualizar botones
    keyboard = [
        [InlineKeyboardButton(f"Suscribirse a 15m", callback_data='suscribir_15m')],
        [InlineKeyboardButton(f"Suscribirse a 1h", callback_data='suscribir_1h')],
        [InlineKeyboardButton(f"Suscribirse a 4h", callback_data='suscribir_4h')],
        [InlineKeyboardButton(f"Suscribirse a 1d", callback_data='suscribir_1d')],
        [InlineKeyboardButton(f"Desuscribirse", callback_data='desuscribir')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)

# Configuración del programa principal
def main():
    # Token de Telegram
    token = os.getenv('TELEGRAM_TOKEN')

    # Inicializar el bot de Telegram
    application = Application.builder().token(token).build()

    # Crear la base de datos
    create_db()

    # Comandos del bot
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    # Programar el envío periódico de informes
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: enviar_informes(application), 'interval', minutes=15)
    scheduler.start()

    # Iniciar el bot
    application.run_polling()

if __name__ == "__main__":
    main()
