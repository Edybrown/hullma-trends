import os
import logging
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes
)

# Configuración del token desde variable de entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Configuración del logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Configuración de la base de datos SQLite
DB_NAME = "usuarios_telegram.db"

def init_db():
    """Inicializa la base de datos SQLite."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            chat_id INTEGER UNIQUE,
            suscripcion_15m BOOLEAN DEFAULT 0,
            suscripcion_1h BOOLEAN DEFAULT 0,
            suscripcion_4h BOOLEAN DEFAULT 0,
            suscripcion_1d BOOLEAN DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def suscribirse(chat_id, suscripcion):
    """Función para suscribir al usuario a una temporalidad."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE usuarios 
        SET {suscripcion} = 1 
        WHERE chat_id = ?
    """, (chat_id,))
    conn.commit()
    conn.close()

def desuscribirse(chat_id, suscripcion):
    """Función para desuscribir al usuario de una temporalidad."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE usuarios 
        SET {suscripcion} = 0 
        WHERE chat_id = ?
    """, (chat_id,))
    conn.commit()
    conn.close()

# Función para manejar /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje de bienvenida con opciones."""
    keyboard = [
        [InlineKeyboardButton("Suscribirse a 15 minutos", callback_data="suscribirse_15m")],
        [InlineKeyboardButton("Suscribirse a 1 hora", callback_data="suscribirse_1h")],
        [InlineKeyboardButton("Suscribirse a 4 horas", callback_data="suscribirse_4h")],
        [InlineKeyboardButton("Suscribirse a 1 día", callback_data="suscribirse_1d")],
        [InlineKeyboardButton("Desuscribirse", callback_data="desuscribirse")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Bienvenido al bot. Seleccione una opción:",
        reply_markup=reply_markup
    )

# Función para manejar botones
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los eventos de los botones."""
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    
    if query.data.startswith("suscribirse"):
        suscripcion = query.data.split("_")[1]
        suscribirse(chat_id, f"suscripcion_{suscripcion}")
        await query.edit_message_text(f"Te has suscrito a la temporalidad de {suscripcion}.")
    
    elif query.data == "desuscribirse":
        # Desuscribir de todas las temporalidades
        for tiempo in ["15m", "1h", "4h", "1d"]:
            desuscribirse(chat_id, f"suscripcion_{tiempo}")
        await query.edit_message_text("Te has desuscrito de todas las temporalidades.")

# Configuración principal
async def run_bot():
    """Función principal para configurar y ejecutar el bot."""
    # Inicializa la base de datos
    init_db()

    # Configurar la aplicación de Telegram
    application = Application.builder().token(TOKEN).build()

    # Añadir handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Ejecutar polling
    print("Bot iniciado y escuchando...")
    await application.run_polling()

# Ejecutar el script
if __name__ == "__main__":
    asyncio.run(run_bot())
