import os
import asyncio
import logging
from datetime import datetime, timedelta
import aiosqlite
from telegram.ext import Application
from telegram.error import TelegramError
import sqlite3
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, ContextTypes
import time
from datetime import datetime, timedelta
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler


reports_dir = "Analisis_trading"
last_report_file = 'last_report.txt'

# Cargar variables de entorno

# Configuración del bot

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
REPORTS_DIR = "Analisis_trading"
TEMPORALIDADES = ['15m', '1h', '4h', '1d']
MAX_RETRIES = 8
RETRY_INTERVAL = 15
DB_NAME = 'usuarios_telegram.db'

async def create_db():
    """Creates the database if it doesn't exist."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute('''
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
            await db.commit()
        logger.info("Database created or already exists.")
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        raise

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

async def check_initial_reports():
    """Verifies that the reports for all timeframes exist."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    for temporalidad in TEMPORALIDADES:
        report_path = os.path.join(REPORTS_DIR, f"report_{temporalidad}.md")
        if os.path.exists(report_path):
            logger.info(f"File found: {report_path}")
        else:
            logger.error(f"Missing file: {report_path}")
            raise FileNotFoundError(f"The report file for timeframe '{temporalidad}' does not exist.")

async def is_report_updated(report_file, last_mod_times):
    """Checks if a report has been updated since the last check."""
    try:
        if os.path.exists(report_file):
            last_mod_time = os.path.getmtime(report_file)
            if last_mod_times.get(report_file) != last_mod_time:
                last_mod_times[report_file] = last_mod_time
                logger.info(f"Updated report detected: {report_file}")
                return True
    except Exception as e:
        logger.error(f"Error checking report update for {report_file}: {e}")
    return False

async def get_time_to_close():
    """Calculates the time remaining until the next candle closure."""
    current_time = datetime.now()
    next_close_time = current_time.replace(second=0, microsecond=0) + timedelta(minutes=15 - (current_time.minute % 15))
    remaining_time = (next_close_time - current_time).total_seconds()
    logger.info(f"Time until next candle closure: {remaining_time} seconds.")
    return remaining_time

async def send_report(chat_id, temporalidad, bot):
    """Envía el informe correspondiente para la temporalidad."""
    report_path = os.path.join(REPORTS_DIR, f"report_{temporalidad}.md")
    
    try:
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as file:
                report_content = file.read()
            await bot.send_message(chat_id=chat_id, text=report_content)
            logger.info(f"Informe de {temporalidad} enviado al chat_id: {chat_id}.")
        else:
            await bot.send_message(chat_id, text=f"El informe de {temporalidad} no está disponible.")
            logger.warning(f"Informe de {temporalidad} no encontrado para el chat_id: {chat_id}.")
    except TelegramError as e:
        if "HTTPXRequest is not initialized" in str(e):
            logger.warning(f"El bot se está cerrando. Se omite el envío del informe de {temporalidad} al {chat_id}.")
        else:
            logger.error(f"Error de Telegram al enviar el informe {temporalidad} al {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Error al enviar el informe {temporalidad} al {chat_id}: {e}")
        
async def check_and_send_reports(chat_id, suscripciones, bot, last_mod_times):
    """Sends reports to a user based on their subscriptions."""
    for temporalidad in reversed(TEMPORALIDADES):
        if temporalidad in suscripciones:
            report_path = os.path.join(REPORTS_DIR, f"report_{temporalidad}.md")
            if await is_report_updated(report_path, last_mod_times):
                await send_report(chat_id, temporalidad, bot)

async def send_reports_to_all_users(bot, last_mod_times):
    """Checks subscriptions and sends updated reports to all users."""
    all_subscriptions = await get_all_user_subscriptions()
    
    for chat_id, suscripciones in all_subscriptions.items():
        logger.info(f"Checking and sending reports for chat_id: {chat_id}.")
        await check_and_send_reports(chat_id, suscripciones, bot, last_mod_times)

async def handle_candle_closure(bot):
    """Maneja el ciclo de cierre de velas."""
    last_mod_times = {}
    while True:
        try:
            logger.info("Iniciando ciclo de cierre de vela.")
            
            await send_reports_to_all_users(bot, last_mod_times)
            
            time_to_close = await get_time_to_close()
            
            for retry in range(MAX_RETRIES):
                logger.info(f"Intento {retry + 1} de {MAX_RETRIES}.")
                try:
                    await asyncio.sleep(RETRY_INTERVAL)
                except asyncio.CancelledError:
                    logger.info("Manejo de cierre de vela interrumpido.")
                    return
                await send_reports_to_all_users(bot, last_mod_times)

            logger.info("No se detectaron actualizaciones. Calculando próximo cierre de vela.")
            time_to_close = await get_time_to_close()
            try:
                await asyncio.sleep(time_to_close)
            except asyncio.CancelledError:
                logger.info("Manejo de cierre de vela interrumpido.")
                return
        except Exception as e:
            logger.error(f"Error en el ciclo de cierre de vela: {e}")
            await asyncio.sleep(60)  # Esperar un minuto antes de reintentar

async def get_all_user_subscriptions():
    """Gets a dictionary with all user subscriptions."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute("SELECT chat_id, suscripciones FROM usuarios") as cursor:
                subscriptions = await cursor.fetchall()

        return {chat_id: suscripciones.split(',') if suscripciones else [] for chat_id, suscripciones in subscriptions}
    except Exception as e:
        logger.error(f"Error getting user subscriptions: {e}")
        return {}

async def main():
    try:
        # Crear la base de datos si no existe
        await create_db()
        
        # Verificar los informes iniciales
        await check_initial_reports()

        # Configurar el bot
        bot_token = os.getenv('TELEGRAM_TOKEN')
        if not bot_token:
            raise ValueError("La variable de entorno TELEGRAM_TOKEN no está configurada")
        
        application = Application.builder().token(bot_token).build()
        
        # Inicializar la aplicación
        await application.initialize()
        
        # Iniciar el manejo del cierre de velas
        candle_closure_task = asyncio.create_task(handle_candle_closure(application.bot))
        
        # Iniciar la aplicación
        await application.start()
        
        # Ejecutar el bot hasta que se presione Ctrl-C
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Error crítico en la función principal: {e}")
    finally:
        # Asegurar el cierre adecuado
        if 'application' in locals():
            await application.stop()
            await application.shutdown()
        
        # Cancelar todas las tareas en ejecución
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
        
        # Esperar a que todas las tareas se completen
        await asyncio.gather(*asyncio.all_tasks(), return_exceptions=True)
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot detenido por el usuario.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")        
