import os
import asyncio
import logging
from datetime import datetime, timedelta
import sqlite3
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
    """Sends the corresponding report for the timeframe."""
    report_path = os.path.join(REPORTS_DIR, f"report_{temporalidad}.md")
    
    try:
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as file:
                report_content = file.read()
            await bot.send_message(chat_id=chat_id, text=report_content)
            logger.info(f"Report for {temporalidad} sent to chat_id: {chat_id}.")
        else:
            await bot.send_message(chat_id, text=f"The report for {temporalidad} is not available.")
            logger.warning(f"Report for {temporalidad} not found for chat_id: {chat_id}.")
    except TelegramError as e:
        logger.error(f"Telegram error sending report {temporalidad} to {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Error sending report {temporalidad} to {chat_id}: {e}")

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
    """Handles the candle closure cycle."""
    last_mod_times = {}
    while True:
        try:
            logger.info("Starting candle closure cycle.")
            
            await send_reports_to_all_users(bot, last_mod_times)
            
            time_to_close = await get_time_to_close()
            
            for retry in range(MAX_RETRIES):
                logger.info(f"Attempt {retry + 1} of {MAX_RETRIES}.")
                await asyncio.sleep(RETRY_INTERVAL)
                await send_reports_to_all_users(bot, last_mod_times)

            logger.info("No updates detected. Calculating next candle closure.")
            time_to_close = await get_time_to_close()
            await asyncio.sleep(time_to_close)
        except Exception as e:
            logger.error(f"Error in candle closure cycle: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying

async def get_all_user_subscriptions():
    """Gets a dictionary with all user subscriptions."""
    try:
        async with aiosqlite.connect('usuarios_telegram.db') as db:
            async with db.execute("SELECT chat_id, suscripciones FROM usuarios") as cursor:
                subscriptions = await cursor.fetchall()

        return {chat_id: suscripciones.split(',') if suscripciones else [] for chat_id, suscripciones in subscriptions}
    except Exception as e:
        logger.error(f"Error getting user subscriptions: {e}")
        return {}

async def main():
    try:
        # Create database if it doesn't exist
        await create_db()
        
        # Verify initial reports
        await check_initial_reports()

        # Configure the bot
        bot = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
        
        # Start the candle closure handling
        asyncio.create_task(handle_candle_closure(bot))
        
        # Start polling
        await bot.run_polling()
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")

if __name__ == "__main__":
    asyncio.run(main())
