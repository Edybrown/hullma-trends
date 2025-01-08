import os
import sqlite3
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

# Cargar variables de entorno
load_dotenv()
bot_token = os.getenv('TELEGRAM_TOKEN')

# Configuración del bot
application = Application.builder().token(bot_token).build()

# Conexión a la base de datos SQLite
def create_db():
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()
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

# Función para guardar un nuevo usuario
def save_user(chat_id, nombre):
    with sqlite3.connect('usuarios_telegram.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,))
        user = c.fetchone()
        
        if not user:
            current_time = datetime.now().isoformat()
            c.execute("INSERT INTO usuarios (chat_id, nombre, suscripciones, suscripcion_fecha, suscripcion_tipo, fecha_ultima_actividad) VALUES (?, ?, '', ?, '', ?)", 
                      (chat_id, nombre, current_time, 'Ninguna', current_time))
            conn.commit()

# Función para obtener la lista de usuarios
def get_users():
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios")
    users = c.fetchall()
    conn.close()
    return users

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    save_user(update.message.chat_id, user.first_name)
    
    # Mensaje de bienvenida con nombre del usuario
    welcome_message = f"¡Hola {user.first_name}! 👋\nBienvenido a nuestro bot. Aquí podrás suscribirte a nuestras temporalidades y recibir actualizaciones periódicas. 😃"
    await update.message.reply_text(welcome_message)
    
    # Mostrar botones de suscripción
    await suscripcion_comando(update, context)

# Función para suscribir/desuscribir usuarios
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data

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
            await query.answer(f"✅ ¡Te has suscrito a Temporalidad {temporalidad}!")
        else:
            await query.answer(f"❌ Ya estás suscrito a Temporalidad {temporalidad}.")
    elif data == 'desuscribir':
        suscripciones = []
        c.execute("UPDATE usuarios SET suscripciones = ? WHERE chat_id = ?",
                  ('', chat_id))
        conn.commit()
        await query.answer("⚠️ Te has desuscrito de todas las temporalidades.")
    
    conn.close()

# Función para enviar informes periódicos
async def enviar_informes(application: Application):
    users = get_users()
    for user in users:
        chat_id = user[1]
        suscripciones = user[3]
        if suscripciones:
            suscripciones_list = ', '.join(suscripciones)
            mensaje = f"Tus suscripciones activas son: {suscripciones_list}.\n¡Gracias por estar con nosotros! 😊"
        else:
            mensaje = "⚠️ No tienes suscripciones activas en este momento."
        await application.bot.send_message(chat_id, mensaje)

# Configuración del programador para enviar informes
def iniciar_programador(application: Application):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        enviar_informes,
        IntervalTrigger(minutes=15),
        args=[application]
    )
    scheduler.start()

# Configuración de botones de suscripción y desuscripción
async def suscripcion_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Suscribirse a Temporalidad 1 ⏳", callback_data='suscribir_1'),
            InlineKeyboardButton("Suscribirse a Temporalidad 2 ⏳", callback_data='suscribir_2')
        ],
        [InlineKeyboardButton("Desuscribirse 🛑", callback_data='desuscribir')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Enviar el mensaje con los botones
    await update.message.reply_text('Selecciona una opción para gestionar tus suscripciones:', reply_markup=reply_markup)

# Main
def main():
    create_db()  # Asegurarse de que la base de datos esté configurada

    # Configurar el manejador de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("suscripcion", suscripcion_comando))
    application.add_handler(CallbackQueryHandler(button))

    iniciar_programador(application)  # Iniciar el envío de informes periódicos

    # Iniciar el bot
    application.run_polling()

if __name__ == '__main__':
    main()
