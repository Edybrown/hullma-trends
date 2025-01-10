import os
import asyncio
import logging
from datetime import datetime, timedelta
import aiosqlite
from telegram.ext import Application
from telegram.error import TelegramError

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
