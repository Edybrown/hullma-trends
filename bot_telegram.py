import asyncio
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import aiosqlite


# Cargar variables de entorno
load_dotenv()
bot_token = os.getenv('TELEGRAM_TOKEN')

# Conexión a la base de datos SQLite
def create_db():
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            chat_id INTEGER UNIQUE,
            nombre TEXT,
            suscripciones TEXT,
            suscripcion_tipo TEXT,
            suscripcion_fecha TIMESTAMP,
            fecha_ultima_actividad TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Función para guardar un nuevo usuario
def save_user(chat_id, nombre):
    with sqlite3.connect('usuarios_telegram.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,))
        user = c.fetchone()
        
        if not user:
            current_time = datetime.now().isoformat()
            c.execute("INSERT INTO usuarios (chat_id, nombre, suscripciones, suscripcion_fecha, suscripcion_tipo, fecha_ultima_actividad) VALUES (?, ?, ?, ?, ?, ?)", 
                      (chat_id, nombre, '', current_time, 'Ninguna', current_time))
            conn.commit()

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    save_user(update.message.chat_id, user.first_name)
    
    welcome_message = (
        f"¡Hola, {user.first_name}! 👋\n\n"
        "¡Bienvenido a tu asistente de análisis de tendencias de trading! 🚀\n\n"
        "Este bot te ayudará a recibir actualizaciones y análisis de trading basados en diferentes temporalidades.\n\n"
        "Puedes suscribirte a cualquiera de las siguientes temporalidades:\n"
        "🔹 15 minutos (15m)\n"
        "🔸 1 hora (1h)\n"
        "🔹 4 horas (4h)\n"
        "🔸 1 día (1d)\n\n"
        "Al suscribirte, recibirás análisis en tiempo real y podrás tomar decisiones más informadas. 🧠💡\n\n"
        "Para comenzar, simplemente selecciona una temporalidad para suscribirte o desuscribirte utilizando los botones a continuación. ¡Empecemos! ⚡"
    )

    keyboard = [[InlineKeyboardButton("Suscripción", callback_data='suscripcion')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message)
    await update.message.reply_text("Selecciona una opción:", reply_markup=reply_markup)

async def show_temporalidades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()
    c.execute("SELECT suscripciones FROM usuarios WHERE chat_id = ?", (chat_id,))
    suscripciones = c.fetchone()
    
    if suscripciones:
        suscripciones = suscripciones[0].split(',') if suscripciones[0] else []
    else:
        suscripciones = []

    keyboard = []
    temporalidades = ['15m', '1h', '4h', '1d']
    for temporalidad in temporalidades:
        if temporalidad in suscripciones:
            button_text = f"Desuscribirse {temporalidad}"
            callback_data = f"desuscribir_{temporalidad}"
        else:
            button_text = f"Suscribirse {temporalidad}"
            callback_data = f"suscribir_{temporalidad}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text('Selecciona una temporalidad para suscribirte o desuscribirte:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data

    if data == 'suscripcion':
        await show_temporalidades(update, context)
        return

    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()
    c.execute("SELECT suscripciones FROM usuarios WHERE chat_id = ?", (chat_id,))
    suscripciones = c.fetchone()

    if suscripciones:
        suscripciones = suscripciones[0].split(',') if suscripciones[0] else []
    else:
        suscripciones = []

    if data.startswith('suscribir'):
        temporalidad = data.split('_')[1]
        if temporalidad not in suscripciones:
            suscripciones.append(temporalidad)
            c.execute("UPDATE usuarios SET suscripciones = ? WHERE chat_id = ?",
                      (','.join(suscripciones), chat_id))
            conn.commit()
            await query.answer(f"Te has suscrito a la temporalidad {temporalidad}.")
        else:
            await query.answer(f"Ya estás suscrito a la temporalidad {temporalidad}.")
    elif data.startswith('desuscribir'):
        temporalidad = data.split('_')[1]
        if temporalidad in suscripciones:
            suscripciones.remove(temporalidad)
            c.execute("UPDATE usuarios SET suscripciones = ? WHERE chat_id = ?",
                      (','.join(suscripciones), chat_id))
            conn.commit()
            await query.answer(f"Te has desuscrito de la temporalidad {temporalidad}.")
        else:
            await query.answer(f"No estás suscrito a la temporalidad {temporalidad}.")

    conn.close()
    await show_temporalidades(update, context)


async def main():
    create_db()
    load_dotenv()
    bot_token = os.getenv('TELEGRAM_TOKEN')
    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CallbackQueryHandler(show_temporalidades, pattern='^suscripcion$'))

    await application.initialize() # Inicializar la app
    asyncio.create_task(handle_candle_closure(application)) # Lanzar tarea en segundo plano
    await application.run_polling(allowed_updates=Update.ALL_TYPES) # Iniciar el polling

if __name__ == "__main__":
    asyncio.run(main())
