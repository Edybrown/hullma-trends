import os
import asyncio
import logging
from datetime import datetime, timedelta
import aiosqlite
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.error import TelegramError

# Configuración
load_dotenv()
REPORTS_DIR = "Analisis_trading"
TEMPORALIDADES = ['15m', '1h', '4h', '1d']
MAX_RETRIES = 3
RETRY_INTERVAL = 5
DB_NAME = 'usuarios_telegram.db'

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Función para crear la base de datos de usuarios
async def create_db():
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
        logger.info("Base de datos creada o ya existente.")
    except Exception as e:
        logger.error(f"Error al crear la base de datos: {e}")
        raise

# Función para guardar a un usuario en la base de datos
async def save_user(chat_id, nombre):
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,))
            user = await cursor.fetchone()
            if not user:
                current_time = datetime.now().isoformat()
                await db.execute(
                    "INSERT INTO usuarios (chat_id, nombre, suscripciones, suscripcion_fecha, suscripcion_tipo, fecha_ultima_actividad) VALUES (?, ?, ?, ?, ?, ?)",
                    (chat_id, nombre, '', current_time, 'Ninguna', current_time)
                )
                await db.commit()
    except Exception as e:
        logger.error(f"Error al guardar usuario: {e}")

# Función para obtener las suscripciones de un usuario
async def get_user_subscriptions(chat_id):
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT suscripciones FROM usuarios WHERE chat_id = ?", (chat_id,))
            suscripciones_data = await cursor.fetchone()
            return suscripciones_data[0].split(',') if suscripciones_data and suscripciones_data[0] else []
    except Exception as e:
        logger.error(f"Error al obtener suscripciones del usuario: {e}")
        return []

# Función para obtener las suscripciones de todos los usuarios
async def get_all_user_subscriptions():
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT chat_id, suscripciones FROM usuarios")
            subscriptions_data = await cursor.fetchall()
        return {chat_id: suscripciones.split(',') if suscripciones else [] for chat_id, suscripciones in subscriptions_data}
    except Exception as e:
        logger.error(f"Error al obtener suscripciones de usuarios: {e}")
        return {}

# Comando /start
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    await save_user(update.message.chat_id, user.first_name)

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

# Función para mostrar los botones de suscripción fijos
async def show_subscription_button(update: Update):
    keyboard = [
        [InlineKeyboardButton("Suscripción", callback_data='suscripcion')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una opción:", reply_markup=reply_markup)

# Función para mostrar las temporalidades disponibles
async def show_temporalidades(update: Update, context: CallbackContext):
    chat_id = update.callback_query.message.chat_id
    suscripciones = await get_user_subscriptions(chat_id)

    if suscripciones is None or suscripciones == ['']:
        suscripciones = []

    keyboard = []
    temporalidades = ['15m', '1h', '4h', '1d']
    for temporalidad in temporalidades:
        button_text = f"{'Desuscribirse' if temporalidad in suscripciones else 'Suscribirse'} {temporalidad}"
        callback_data = f"{'desuscribir' if temporalidad in suscripciones else 'suscribir'}_{temporalidad}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text('Selecciona una temporalidad para suscribirte o desuscribirte:', reply_markup=reply_markup)

# Función para manejar las acciones de suscripción y desuscripción
async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            suscripciones = await get_user_subscriptions(chat_id)
            if suscripciones is None or suscripciones == ['']:
                suscripciones = []

            accion, temporalidad = data.split('_', 1)

            if accion == 'suscribir':
                if temporalidad not in suscripciones:
                    suscripciones.append(temporalidad)
                    await query.answer(f"Te has suscrito a {temporalidad}.")
                else:
                    await query.answer(f"Ya estás suscrito a {temporalidad}.")
            elif accion == 'desuscribir':
                if temporalidad in suscripciones:
                    suscripciones.remove(temporalidad)
                    await query.answer(f"Te has desuscrito de {temporalidad}.")
                else:
                    await query.answer(f"No estás suscrito a {temporalidad}.")

            await db.execute("UPDATE usuarios SET suscripciones = ? WHERE chat_id = ?", (','.join(suscripciones), chat_id))
            await db.commit()
    except Exception as e:
        logger.error(f"Error al manejar el botón: {e}")
        await query.answer("Ocurrió un error.")
        return

    await show_temporalidades(update, context)

# Función para enviar el informe de la temporalidad
async def send_report(chat_id, temporalidad, bot):
    report_path = os.path.join(REPORTS_DIR, f"report_{temporalidad}.md")
    try:
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as file:
                report_content = file.read()
            await bot.send_message(chat_id=chat_id, text=report_content)
            logger.info(f"Informe de {temporalidad} enviado al chat_id: {chat_id}.")
        else:
            logger.warning(f"Informe de {temporalidad} no encontrado para el chat_id: {chat_id}.")
            await bot.send_message(chat_id, text=f"El informe de {temporalidad} no está disponible.")
    except TelegramError as e:
        logger.error(f"Error de Telegram al enviar el informe {temporalidad} a {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Error al enviar el informe {temporalidad} a {chat_id}: {e}")

# Función principal para ejecutar el bot
async def main():
    application = None
    try:
        await create_db()

        bot_token = os.getenv('TELEGRAM_TOKEN')
        if not bot_token:
            raise ValueError("La variable de entorno TELEGRAM_TOKEN no está configurada")

        application = Application.builder().token(bot_token).build()

        # Añadir handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button))
        application.add_handler(CallbackQueryHandler(show_temporalidades, pattern='^suscripcion$'))  # Patrón para el botón principal

        await application.run_polling(allowed_updates=Update.ALL_TYPES) # Con paréntesis
        await application.idle()

    except Exception as e:
        logger.critical(f"Error crítico en la función principal: {e}")
    finally:
        if application:
            try:
                await application.stop()
                await application.shutdown()
            except Exception as e:
                logger.error(f"Error al detener la aplicación: {e}")
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot detenido por el usuario.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
