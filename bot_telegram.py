import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Leer el token desde las variables de entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Configuración de la base de datos SQLite
DB_NAME = "usuarios_telegram.db"

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            username TEXT,
            temporalidades TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user_to_db(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO usuarios (id, username, temporalidades) VALUES (?, ?, ?)", 
                   (user_id, username, ""))
    conn.commit()
    conn.close()

# Inicio del bot y mensaje de bienvenida
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    add_user_to_db(user.id, user.username)

    welcome_message = (
        f"¡Hola, {user.first_name}! 👋\n\n"
        "Soy tu bot de análisis de mercado.\n\n"
        "🕒 Temporalidades disponibles: 15 minutos, 1 hora, 4 horas, y 1 día.\n"
        "🔔 Recibirás análisis cada cierre de vela según tus preferencias.\n"
        "📝 Usa el botón 'Gestionar Suscripciones' para suscribirte o modificar tus opciones."
    )
    keyboard = [
        [InlineKeyboardButton("Gestionar Suscripciones", callback_data="gestionar_suscripciones")],
        [InlineKeyboardButton("Estado de Mis Suscripciones", callback_data="estado_suscripciones")],
        [InlineKeyboardButton("Detener Suscripciones", callback_data="detener_suscripciones")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(welcome_message, reply_markup=reply_markup)

# Callback para gestionar las suscripciones
def handle_callbacks(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == "gestionar_suscripciones":
        query.edit_message_text(
            "Aquí puedes suscribirte o desuscribirte de las temporalidades.\n"
            "🔹 15m, 🔹 1h, 🔹 4h, 🔹 1d\n\n"
            "Selecciona una opción para continuar.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Suscribirse a 15m", callback_data="suscribir_15m")],
                [InlineKeyboardButton("Desuscribirse de 15m", callback_data="desuscribir_15m")],
                [InlineKeyboardButton("Volver", callback_data="volver_inicio")]
            ])
        )
    elif query.data == "volver_inicio":
        start(update, context)  # Volver al inicio

# Configuración del bot
def main():
    # Configurar la base de datos
    setup_database()

    # Configurar el bot
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Comandos
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(handle_callbacks))

    # Iniciar el bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
