import os
import asyncio
import aiosqlite
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, ContextTypes, ApplicationBuilder
from datetime import datetime, timedelta

reports_dir = "Analisis_trading"

load_dotenv()
bot_token = os.getenv('TELEGRAM_TOKEN')

application = Application.builder().token(bot_token).build()

async def create_db():
    try:
        async with aiosqlite.connect('usuarios_telegram.db') as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY,
                    chat_id INTEGER UNIQUE,
                    nombre TEXT,
                    suscripciones TEXT,
                    suscripcion_tipo TEXT,
                    suscripcion_fecha TIMESTAMP,
                    fecha_ultima_actividad TIMESTAMP
                )
            """)
            await conn.commit()
    except aiosqlite.Error as e:
        print(f"[ERROR] Error al crear la base de datos: {e}")

async def save_user(chat_id, nombre):
    try:
        async with aiosqlite.connect('usuarios_telegram.db') as conn:
            async with conn.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,)) as cursor:
                user = await cursor.fetchone()
                if not user:
                    current_time = datetime.now().isoformat()
                    await conn.execute("INSERT INTO usuarios (chat_id, nombre, suscripciones, suscripcion_fecha, fecha_ultima_actividad) VALUES (?, ?, '', ?, '', ?)", (chat_id, nombre, current_time, 'Ninguna', current_time))
                    await conn.commit()
    except aiosqlite.Error as e:
        print(f"[ERROR] Error al guardar el usuario: {e}")

async def get_users():
    try:
        async with aiosqlite.connect('usuarios_telegram.db') as conn:
            async with conn.execute("SELECT * FROM usuarios") as cursor:
                return await cursor.fetchall()
    except aiosqlite.Error as e:
        print(f"[ERROR] Error al obtener los usuarios: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await save_user(update.message.chat_id, user.first_name)
    welcome_message = f"¡Hola, {user.first_name}! \n\nBienvenido a tu asistente de análisis de tendencias de trading! \n\nEste bot te ayudará a recibir actualizaciones y análisis de trading basados en diferentes temporalidades.\n\nPuedes suscribirte a cualquiera de las siguientes temporalidades:\n 15 minutos (15m)\n 1 hora (1h)\n 4 horas (4h)\n 1 día (1d)\n\nAl suscribirte, recibirás análisis en tiempo real y podrás tomar decisiones más informadas. \n\nPara comenzar, simplemente selecciona una temporalidad para suscribirte o desuscribirte utilizando los botones a continuación. ¡Empecemos! ⚡"
    await update.message.reply_text(welcome_message)
    await show_subscription_button(update)

async def show_subscription_button(update: Update):
    keyboard = [[InlineKeyboardButton("Suscripción", callback_data='suscripcion')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una opción:", reply_markup=reply_markup)

async def show_temporalidades(update: Update, context: CallbackContext):
    chat_id = update.callback_query.message.chat_id
    try:
        async with aiosqlite.connect('usuarios_telegram.db') as conn:
            async with conn.execute("SELECT suscripciones FROM usuarios WHERE chat_id = ?", (chat_id,)) as cursor:
                suscripciones_db = await cursor.fetchone()
    except aiosqlite.Error as e:
        print(f"[ERROR] Error al obtener las suscripciones del usuario: {e}")
        return

    suscripciones = suscripciones_db[0].split(',') if suscripciones_db and suscripciones_db[0] else []

    keyboard = []
    temporalidades = ['15m', '1h', '4h', '1d']
    for temporalidad in temporalidades:
        button_text = f"{'Desuscribirse' if temporalidad in suscripciones else 'Suscribirse'} {temporalidad}"
        callback_data = f"{'desuscribir' if temporalidad in suscripciones else 'suscribir'}_{temporalidad}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text('Selecciona una temporalidad:', reply_markup=reply_markup)

async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data
    try:
        async with aiosqlite.connect('usuarios_telegram.db') as conn:
            async with conn.execute("SELECT suscripciones FROM usuarios WHERE chat_id = ?", (chat_id,)) as cursor:
                suscripciones_db = await cursor.fetchone()
            suscripciones = suscripciones_db[0].split(',') if suscripciones_db and suscripciones_db[0] else []

            temporalidad = data.split('_')[1]
            accion = data.split('_')[0]

            if accion == 'suscribir' and temporalidad not in suscripciones:
                suscripciones.append(temporalidad)
                await query.answer(f"Te has suscrito a {temporalidad}.")
            elif accion == 'desuscribir' and temporalidad in suscripciones:
                suscripciones.remove(temporalidad)
                await query.answer(f"Te has desuscrito de {temporalidad}.")
            else:
                await query.answer(f"Ya estás {'suscrito' if temporalidad in suscripciones else 'desuscrito'} a {temporalidad}.")

            await conn.execute("UPDATE usuarios SET suscripciones = ? WHERE chat_id = ?", (','.join(suscripciones), chat_id))
            await conn.commit()

    except aiosqlite.Error as e:
        print(f"[ERROR] Error al actualizar las suscripciones: {e}")
        await query.answer("Ocurrió un error al procesar tu solicitud.")
        return

    await show_temporalidades(update, context)

def check_initial_reports():
    temporalidades = ['15m', '1h', '4h', '1d']
    os.makedirs(reports_dir, exist_ok=True)
    for temporalidad in temporalidades:
        report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
        if not os.path.exists(report_path):
            raise FileNotFoundError(f"El archivo de informe para la temporalidad '{temporalidad}' no existe.")

def get_time_to_close():
    current_time = datetime.now()
    next_close_time = current_time.replace(second=0, microsecond=0) + timedelta(minutes=15 - (current_time.minute % 15))
    remaining_time = (next_close_time - current_time).total_seconds()
    print(f"[INFO] Tiempo hasta el próximo cierre de vela: {remaining_time} segundos.")
    return remaining_time



async def send_report(chat_id, temporalidad, bot):
    report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
    if os.path.exists(report_path):
        with open(report_path, 'r') as file:
            report_content = file.read()
        try:
            await bot.send_message(chat_id=chat_id, text=report_content)
            print(f"[INFO] Informe de {temporalidad} enviado a chat_id: {chat_id}.")
        except Exception as e: # Captura excepciones de Telegram
            print(f"[ERROR] Error al enviar mensaje a {chat_id}: {e}")
    else:
        print(f"[WARNING] Informe de {temporalidad} no encontrado para chat_id: {chat_id}.")


async def check_and_send_reports(chat_id, suscripciones, bot):
    temporalidades = ['1d', '4h', '1h', '15m']
    for temporalidad in temporalidades:
        if temporalidad in suscripciones:
            await send_report(chat_id, temporalidad, bot)

async def send_reports_to_all_users(bot):
    all_subscriptions = await get_all_user_subscriptions()
    for chat_id, suscripciones in all_subscriptions.items():
        await check_and_send_reports(chat_id, suscripciones, bot)

async def handle_candle_closure(bot):
    while True:
        print("[INFO] Iniciando ciclo de cierre de vela.")
        await check_and_send_reports(bot)
        time_to_close = get_time_to_close()
        print(f"[INFO] Esperando {time_to_close} segundos hasta el próximo cierre de vela.")
        await asyncio.sleep(time_to_close)



def check_initial_reports():
    temporalidades = ['15m', '1h', '4h', '1d']
    os.makedirs(reports_dir, exist_ok=True)
    for temporalidad in temporalidades:
        report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
        if not os.path.exists(report_path):
            raise FileNotFoundError(f"El archivo de informe para la temporalidad '{temporalidad}' no existe.")

def get_time_to_close():
    current_time = datetime.now()
    next_close_time = current_time.replace(second=0, microsecond=0) + timedelta(minutes=15 - (current_time.minute % 15))
    remaining_time = (next_close_time - current_time).total_seconds()
    print(f"[INFO] Tiempo hasta el próximo cierre de vela: {remaining_time} segundos.")
    return remaining_time

async def get_all_user_subscriptions():
    try:
        async with aiosqlite.connect('usuarios_telegram.db') as conn:
            async with conn.execute("SELECT chat_id, suscripciones FROM usuarios") as cursor:
                subscriptions = await cursor.fetchall()
        subscriptions_dict = {}
        for chat_id, suscripciones in subscriptions:
            subscriptions_dict[chat_id] = suscripciones.split(',') if suscripciones else []
        return subscriptions_dict
    except aiosqlite.Error as e:
        print(f"[ERROR] Error al obtener las suscripciones: {e}")
        return {}

def main():
    # Configuración inicial
    print("[INFO] Configurando el bot...")
    asyncio.run(create_db())  # Sincronización de la base de datos
    check_initial_reports()  # Verificar informes iniciales
    get_all_user_subscriptions()
    # Obtener el token desde la variable de entorno
    bot_token = os.getenv("TELEGRAM_TOKEN")
    if not bot_token:
        raise ValueError("El token del bot no está configurado en las variables de entorno.")

    # Crear la aplicación del bot
    application = ApplicationBuilder().token(bot_token).build()

    # Agregar manejadores (handlers)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_temporalidades, pattern='^suscripcion$'))
    application.add_handler(CallbackQueryHandler(button))

   

    # Iniciar el bot (la librería maneja el bucle de eventos)
    print("[INFO] Iniciando el bot...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
