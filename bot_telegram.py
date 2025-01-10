import os
import aiosqlite
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, ContextTypes
from datetime import datetime
import os
import time
from datetime import datetime, timedelta
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler


reports_dir = "Analisis_trading"
last_report_file = 'last_report.txt'

# Cargar variables de entorno
load_dotenv()
bot_token = os.getenv('TELEGRAM_TOKEN')

# Configuración del bot
application = Application.builder().token(bot_token).build()

# Conexión a la base de datos SQLite
async def create_db():
    async with aiosqlite.connect('usuarios_telegram.db') as conn:
        await conn.execute('''
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
        await conn.commit()

# Función para guardar un nuevo usuario
async def save_user(chat_id, nombre):
    async with aiosqlite.connect('usuarios_telegram.db') as conn:
        async with conn.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                current_time = datetime.now().isoformat()
                await conn.execute("INSERT INTO usuarios (chat_id, nombre, suscripciones, suscripcion_fecha, suscripcion_tipo, fecha_ultima_actividad) VALUES (?, ?, '', ?, '', ?)",
                                 (chat_id, nombre, current_time, 'Ninguna', current_time))
                await conn.commit()
                
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
    """Calcula el tiempo restante para el próximo cierre de vela."""
    current_time = datetime.now()
    next_close_time = current_time.replace(second=0, microsecond=0) + timedelta(minutes=15 - (current_time.minute % 15))
    remaining_time = (next_close_time - current_time).total_seconds()
    print(f"[INFO] Tiempo hasta el próximo cierre de vela: {remaining_time} segundos.")
    return remaining_time

# Envía un informe a un usuario
async def send_report(chat_id, temporalidad, bot):
    """Envía el informe correspondiente a la temporalidad."""
    report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
    
    if os.path.exists(report_path):
        with open(report_path, 'r') as file:
            report_content = file.read()
        await bot.send_message(chat_id=chat_id, text=report_content)
        print(f"[INFO] Informe de {temporalidad} enviado a chat_id: {chat_id}.")
    else:
        await bot.send_message(chat_id, text=f"El informe de {temporalidad} no está disponible.")
        print(f"[WARNING] Informe de {temporalidad} no encontrado para chat_id: {chat_id}.")

# Revisa y envía los informes según las suscripciones
async def check_and_send_reports(chat_id, suscripciones, bot):
    # ... (esta función se mantiene similar, pero sin el manejo de last_mod_times)
    temporalidades = ['1d', '4h', '1h', '15m']
    for temporalidad in temporalidades:
        if temporalidad in suscripciones:
            report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
            if os.path.exists(report_path): # Simplificado, se envía si existe
                await send_report(chat_id, temporalidad, bot)


async def send_reports_to_all_users(bot):
    async with aiosqlite.connect('usuarios_telegram.db') as conn:
        async with conn.execute("SELECT chat_id, suscripciones FROM usuarios") as cursor:
            subscriptions = await cursor.fetchall()
    subscriptions_dict = {}
    for chat_id, suscripciones in subscriptions:
        subscriptions_dict[chat_id] = suscripciones.split(',') if suscripciones else []
    for chat_id, suscripciones in subscriptions_dict.items():
        await check_and_send_reports(chat_id, suscripciones, bot)


# Manejo del ciclo de cierre de vela
async def handle_candle_closure(bot):
    while True:
        print("[INFO] Iniciando ciclo de cierre de vela.")
        await send_reports_to_all_users(bot)
        time_to_close = get_time_to_close()
        print(f"[INFO] Esperando {time_to_close} segundos hasta el próximo cierre de vela.")
        await asyncio.sleep(time_to_close)


# Configuración inicial del bot
def get_all_user_subscriptions():
    """Obtiene un diccionario con todas las suscripciones de los usuarios."""
    with sqlite3.connect('usuarios_telegram.db') as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id, suscripciones FROM usuarios")
        subscriptions = c.fetchall()

    # Convertir a formato {chat_id: [temporalidades]}
    subscriptions_dict = {}
    for chat_id, suscripciones in subscriptions:
        if suscripciones:
            subscriptions_dict[chat_id] = suscripciones.split(',')
        else:
            subscriptions_dict[chat_id] = []
    
    return subscriptions_dict

# Modificar la función main
async def main():
    await create_db() # Ahora es asíncrona
    check_initial_reports()
    print("[INFO] Bot configurado. Iniciando ciclo de manejo de velas.")
    await handle_candle_closure(application.bot)

if __name__ == '__main__':
    application.run_polling()
    asyncio.run(main())
