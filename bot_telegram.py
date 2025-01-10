import os
import sqlite3
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, ContextTypes
from datetime import datetime
import os
import time
from datetime import datetime, timedelta
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import telegram 

reports_dir = "Analisis_trading"
last_report_file = 'last_report.txt'

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

def check_initial_reports():
    """Verifica que los informes de las temporalidades existen."""
    temporalidades = ['15m', '1h', '4h', '1d']
    os.makedirs(reports_dir, exist_ok=True)  # Asegurar que el directorio existe
    
    for temporalidad in temporalidades:
        report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
        if os.path.exists(report_path):
            print(f"[INFO] Archivo encontrado: {report_path}")
        else:
            print(f"[ERROR] Archivo faltante: {report_path}")
            raise FileNotFoundError(f"El archivo de informe para la temporalidad '{temporalidad}' no existe.")


# Verifica si un archivo ha sido modificado
def is_report_updated(report_file, last_mod_times):
    """Verifica si un informe ha sido actualizado desde la última vez."""
    if os.path.exists(report_file):
        last_mod_time = os.path.getmtime(report_file)
        if last_mod_times.get(report_file) != last_mod_time:
            last_mod_times[report_file] = last_mod_time
            print(f"[INFO] Informe actualizado detectado: {report_file}")
            return True
    return False

# Calcula el tiempo hasta el cierre de la vela
def get_time_to_close():
    current_time = datetime.now()
    next_close_time = current_time.replace(second=0, microsecond=0) + timedelta(minutes=15 - (current_time.minute % 15))
    remaining_time = (next_close_time - current_time).total_seconds()
    print(f"[INFO] Tiempo hasta el próximo cierre de vela: {remaining_time} segundos.")
    return remaining_time


def split_string(text, max_length=4096): #limite de telegram
    """Divide un string en partes más pequeñas."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

async def send_report(chat_id, temporalidad, bot):
    report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
    try:
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as file:
                report_content = file.read()
            messages = split_string(report_content)
            for message in messages:
                await bot.send_message(chat_id=chat_id, text=message, parse_mode=telegram.constants.ParseMode.MARKDOWN)
            print(f"[INFO] Informe de {temporalidad} enviado a chat_id: {chat_id}.")
        else:
            await bot.send_message(chat_id, text=f"El informe de {temporalidad} no está disponible.")
            print(f"[WARNING] Informe de {temporalidad} no encontrado para chat_id: {chat_id}.")
    except telegram.error.TelegramError as e:
        print(f"[ERROR Telegram] Error al enviar informe {temporalidad} a {chat_id}: {e}")
        if e.message == "Too Many Requests":
            await asyncio.sleep(60)
            await send_report(chat_id, temporalidad, bot)
        else:
            try:
                await bot.send_message(chat_id, text=f"Hubo un error al procesar el informe de {temporalidad}. {e.message}")
            except Exception as e2:
                print(f"[CRITICAL] Fallo al enviar mensaje de error a {chat_id}: {e2}")
    except Exception as e:
        print(f"[ERROR General] Error al enviar informe {temporalidad} a {chat_id}: {e}")
        try:
            await bot.send_message(chat_id, text=f"Hubo un error al procesar el informe de {temporalidad}.")
        except Exception as e2:
            print(f"[CRITICAL] Fallo al enviar mensaje de error a {chat_id}: {e2}")


# Revisa y envía los informes según las suscripciones
async def check_and_send_reports(chat_id, suscripciones, bot, last_mod_times):
    """Envía los informes a un usuario en base a sus suscripciones."""
    temporalidades = ['1d', '4h', '1h', '15m']  # Orden de mayor a menor temporalidad
    
    for temporalidad in temporalidades:
        if temporalidad in suscripciones:
            report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
            if is_report_updated(report_path, last_mod_times):
                await send_report(chat_id, temporalidad, bot)

# Enviar informes a todos los usuarios
async def send_reports_to_all_users(bot, last_mod_times):
    """Revisa las suscripciones y envía informes actualizados a todos los usuarios."""
    all_subscriptions = get_all_user_subscriptions()  # Diccionario: {chat_id: ['15m', '1h']}
    
    for chat_id, suscripciones in all_subscriptions.items():
        print(f"[INFO] Revisando y enviando informes para chat_id: {chat_id}.")
        await check_and_send_reports(chat_id, suscripciones, bot, last_mod_times)

# Manejo del ciclo de cierre de vela
async def handle_candle_closure(bot):
    last_mod_times = {}
    while True:
        print("[INFO] Iniciando ciclo de cierre de vela.")
        await send_reports_to_all_users(bot, last_mod_times)
        time_to_close = get_time_to_close()
        print(f"[INFO] Esperando {time_to_close} segundos hasta el próximo cierre de vela.")
        await asyncio.sleep(time_to_close)
        # Si no hay actualizaciones, calcular el tiempo para el próximo cierre
        print("[INFO] No se detectaron actualizaciones. Calculando próximo cierre de vela.")
        time_to_close = get_time_to_close()
        await asyncio.sleep(time_to_close)

# Configuración inicial del bot
def get_all_user_subscriptions():
    with sqlite3.connect('usuarios_telegram.db') as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, suscripciones FROM usuarios")
        subscriptions = c.fetchall()

    subscriptions_dict = {}
    for chat_id, suscripciones in subscriptions:
        subscriptions_dict[chat_id] = suscripciones.split(',') if suscripciones else []
    return subscriptions_dict

# Modificar la función main
async def main():
  create_db()
  check_initial_reports()

  global application  # Make application accessible globally

  application = Application.builder().token(bot_token).build()

  application.add_handler(CommandHandler("start", start))
  application.add_handler(CallbackQueryHandler(button))
  application.add_handler(CallbackQueryHandler(show_temporalidades, pattern='^suscripcion$'))

  # Run the background task for sending reports
  asyncio.create_task(handle_candle_closure(application.bot))

  # Start the polling loop to listen for Telegram events
  await application.run_polling()  # This line is crucial!

if __name__ == "__main__":
  asyncio.run(main())
