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

async def get_user_subscriptions(chat_id): #Obtiene las suscripciones de UN usuario
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("SELECT suscripciones FROM usuarios WHERE chat_id = ?", (chat_id,))
            suscripciones_data = await cursor.fetchone()
            return suscripciones_data[0].split(',') if suscripciones_data and suscripciones_data[0] else []
    except Exception as e:
        logger.error(f"Error al obtener suscripciones del usuario: {e}")
        return []

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
    chat_id = update.callback_query.message.chat_id
    suscripciones = await get_user_subscriptions(chat_id)
    
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

    try:
        async with aiosqlite.connect(DB_NAME) as db:
            suscripciones = await get_user_subscriptions(chat_id)
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
async def check_initial_reports():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    for temporalidad in TEMPORALIDADES:
        report_path = os.path.join(REPORTS_DIR, f"report_{temporalidad}.md")
        if not os.path.exists(report_path):
            logger.error(f"Falta el archivo: {report_path}")
            raise FileNotFoundError(f"Falta el informe para la temporalidad '{temporalidad}'.")
        else:
            logger.info(f"Archivo encontrado: {report_path}")

async def is_report_updated(report_file, last_mod_times):
    try:
        if os.path.exists(report_file):
            last_mod_time = os.path.getmtime(report_file)
            if last_mod_times.get(report_file) != last_mod_time:
                last_mod_times[report_file] = last_mod_time
                logger.info(f"Informe actualizado detectado: {report_file}")
                return True
    except Exception as e:
        logger.error(f"Error al comprobar la actualización del informe {report_file}: {e}")
    return False

async def get_time_to_close():
    current_time = datetime.now()
    next_close_time = current_time.replace(second=0, microsecond=0) + timedelta(minutes=15 - (current_time.minute % 15))
    remaining_time = (next_close_time - current_time).total_seconds()
    logger.info(f"Tiempo hasta el próximo cierre de vela: {remaining_time} segundos.")
    return remaining_time

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

async def check_and_send_reports(chat_id, suscripciones, bot, last_mod_times):
    for temporalidad in TEMPORALIDADES:  # No es necesario reverse, el orden se maneja al enviar
        if temporalidad in suscripciones:
            report_path = os.path.join(REPORTS_DIR, f"report_{temporalidad}.md")
            if await is_report_updated(report_path, last_mod_times):
                await send_report(chat_id, temporalidad, bot)

async def send_reports_to_all_users(bot, last_mod_times):
    all_subscriptions = await get_all_user_subscriptions()
    for chat_id, suscripciones in all_subscriptions.items():
        logger.info(f"Comprobando y enviando informes para chat_id: {chat_id}.")
        await check_and_send_reports(chat_id, suscripciones, bot, last_mod_times)

async def handle_candle_closure(bot):
    last_mod_times = {}
    while True:
        try:
            logger.info("Iniciando ciclo de cierre de vela.")
            await send_reports_to_all_users(bot, last_mod_times)

            time_to_close = await get_time_to_close()
            logger.info(f"Esperando {time_to_close} segundos hasta el próximo ciclo.")
            await asyncio.sleep(time_to_close)

        except asyncio.CancelledError:
            logger.info("Manejo de cierre de vela interrumpido.")
            break # Importante salir del bucle while True si se cancela la tarea
        except Exception as e:
            logger.error(f"Error en el ciclo de cierre de vela: {e}")
            await asyncio.sleep(60)
async def main():
    application = None
    candle_closure_task = None
    try:
        await create_db()
        await check_initial_reports()

        bot_token = os.getenv('TELEGRAM_TOKEN')
        if not bot_token:
            raise ValueError("La variable de entorno TELEGRAM_TOKEN no está configurada")

        application = Application.builder().token(bot_token).build()

        # Añadir handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button))
        application.add_handler(CallbackQueryHandler(show_temporalidades, pattern='^suscripcion$'))  # Patrón para el botón principal

        await application.initialize()
        candle_closure_task = asyncio.create_task(handle_candle_closure(application.bot))

        await application.start_polling(allowed_updates=Update.ALL_TYPES)
        await application.idle()  # Mantener el bot en ejecución

    except Exception as e:
        logger.critical(f"Error crítico en la función principal: {e}")
    finally:
        if application:
            try:
                await application.stop()
                await application.shutdown()
            except Exception as e:
                logger.error(f"Error al detener la aplicación: {e}")

        if candle_closure_task:
            candle_closure_task.cancel()
            try:
                await candle_closure_task  # Esperar a que la tarea se cancele
            except asyncio.CancelledError:
                pass  # Ignorar la excepción CancelledError
            except Exception as e:
                logger.error(f"Error al cancelar la tarea de cierre de vela: {e}")

        # Limpieza final (opcional, pero recomendada)
        await asyncio.gather(*asyncio.all_tasks(), return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot detenido por el usuario.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")            
