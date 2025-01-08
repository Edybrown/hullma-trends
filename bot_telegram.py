import os
import sqlite3
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, ContextTypes
from datetime import datetime
import os
import time
from datetime import datetime
import asyncio


reports_dir = 'Informe Final'


# Cargar variables de entorno
load_dotenv()
bot_token = os.getenv('TELEGRAM_TOKEN')

# Configuración del bot
application = Application.builder().token(bot_token).build()

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
            c.execute("INSERT INTO usuarios (chat_id, nombre, suscripciones, suscripcion_fecha, suscripcion_tipo, fecha_ultima_actividad) VALUES (?, ?, '', ?, '', ?, ?)", 
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
    
    # Mensaje de bienvenida mejorado
    welcome_message = (
        "¡Hola, {name}! 👋\n\n"
        "¡Bienvenido a tu asistente de análisis de tendencias de trading! 🚀\n\n"
        "Este bot te ayudará a recibir actualizaciones y análisis de trading basados en diferentes temporalidades.\n\n"
        "Puedes suscribirte a cualquiera de las siguientes temporalidades:\n"
        "🔹 15 minutos (15m)\n"
        "🔸 1 hora (1h)\n"
        "🔹 4 horas (4h)\n"
        "🔸 1 día (1d)\n\n"
        "Al suscribirte, recibirás análisis en tiempo real y podrás tomar decisiones más informadas. 🧠💡\n\n"
        "Para comenzar, simplemente selecciona una temporalidad para suscribirte o desuscribirte utilizando los botones a continuación. ¡Empecemos! ⚡"
    ).format(name=user.first_name)

    # Mostrar mensaje de bienvenida
    await update.message.reply_text(welcome_message)

    # Llamar a la función para mostrar los botones fijos
    await show_subscription_button(update)


# Función para mostrar botones de suscripción fijos
async def show_subscription_button(update: Update):
    keyboard = [
        [InlineKeyboardButton("Suscripción", callback_data='suscripcion')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una opción:", reply_markup=reply_markup)

# Función para mostrar las temporalidades disponibles
async def show_temporalidades(update: Update, context: CallbackContext):
    chat_id = update.callback_query.message.chat_id  # Cambiado de update.message a update.callback_query.message
    conn = sqlite3.connect('usuarios_telegram.db')
    c = conn.cursor()
    c.execute("SELECT suscripciones FROM usuarios WHERE chat_id = ?", (chat_id,))
    suscripciones = c.fetchone()
    
    if suscripciones:
        suscripciones = suscripciones[0].split(',')
    else:
        suscripciones = []

    # Crear el teclado según las suscripciones actuales
    keyboard = []
    
    # Agregar botones para las temporalidades disponibles
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
    await update.callback_query.message.reply_text('Selecciona una temporalidad para suscribirte o desuscribirte:', reply_markup=reply_markup)


# Función para manejar las acciones de suscripción y desuscripción
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

    # Gestionar las suscripciones
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

    # Actualizar los botones con las nuevas suscripciones
    await show_temporalidades(update, context)
# logica del bot ----------------------------------------------------------------------------------------------------

def get_time_to_close(temporalidad):
    current_time = datetime.now()
    if temporalidad == '15m':
        next_close_time = current_time.replace(second=0, microsecond=0) + timedelta(minutes=15)
    elif temporalidad == '1h':
        next_close_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    elif temporalidad == '4h':
        next_close_time = current_time.replace(hour=(current_time.hour // 4) * 4, minute=0, second=0, microsecond=0) + timedelta(hours=4)
    elif temporalidad == '1d':
        next_close_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return next_close_time

# Función para verificar si el archivo está actualizado
def is_report_updated(temporalidad):
    report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
    # Comprobamos si el archivo existe y si tiene una fecha de actualización reciente
    if os.path.exists(report_path):
        file_time = datetime.fromtimestamp(os.path.getmtime(report_path))
        if datetime.now() - file_time < timedelta(minutes=15):  # Si el archivo fue modificado en los últimos 15 minutos
            return True
    return False

# Función para enviar el informe
async def send_report(context: CallbackContext, chat_id, temporalidad): # Corregido: context como primer argumento
    report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
    if is_report_updated(temporalidad):
        try:
            with open(report_path, 'r', encoding='utf-8') as file: # Añadido encoding='utf-8'
                analysis_message = file.read()
            await context.bot.send_message(chat_id=chat_id, text=analysis_message)
            logger.info(f"Reporte {temporalidad} enviado a {chat_id}")
            return True
        except FileNotFoundError:
            logger.error(f"Archivo no encontrado: {report_path}")
            return False
        except Exception as e:
            logger.error(f"Error al enviar reporte {temporalidad} a {chat_id}: {e}")
            return False
    return False

async def check_and_send_reports(context: CallbackContext, temporalidad):
    while True:
        time_to_close = get_time_to_close(temporalidad)
        now = datetime.now()
        sleep_time = (time_to_close - now).total_seconds()
        if sleep_time > 0:
            logger.info(f"Esperando {sleep_time} segundos para el cierre de {temporalidad}")
            await asyncio.sleep(sleep_time)
        with sqlite3.connect('usuarios_telegram.db') as conn:
            c = conn.cursor()
            c.execute("SELECT chat_id FROM usuarios WHERE suscripciones LIKE ?", ('%'+temporalidad+'%',))
            user_ids = c.fetchall()

        tasks = [send_report(context, user_id[0], temporalidad) for user_id in user_ids]
        await asyncio.gather(*tasks)

async def start_report_tasks(context: CallbackContext):
    temporalidades = ['15m', '1h', '4h', '1d']
    tasks = [asyncio.create_task(check_and_send_reports(context, temporalidad)) for temporalidad in temporalidades]
    await asyncio.gather(*tasks)

async def post_init(application: Application):
    await application.bot.send_message(chat_id=YOUR_ADMIN_CHAT_ID, text="Bot iniciado")
    asyncio.create_task(start_report_tasks(application))

def main():
    create_db()
    application = Application.builder().token(bot_token).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button, pattern='^(suscribir|desuscribir)'))
    application.add_handler(CallbackQueryHandler(show_temporalidades, pattern='^suscripcion'))

    application.run_polling()

if __name__ == '__main__':
    main()
