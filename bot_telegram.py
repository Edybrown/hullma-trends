import time
import traceback
import os
import asyncio
import aiosqlite
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, ContextTypes, ApplicationBuilder
from datetime import datetime, timedelta

reports_dir = "Analisis_trading"
last_checked = {}

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

async def obtener_usuarios_de_db():
    try:
        async with aiosqlite.connect('usuarios_telegram.db') as conn:
            async with conn.execute("SELECT chat_id, suscripciones FROM usuarios") as cursor:
                usuarios = await cursor.fetchall()
                usuarios_dict = {}
                for usuario in usuarios:
                    usuarios_dict[usuario[0]] = usuario[1].split(",") if usuario[1] else [] #Manejo de suscripciones vacias
                return usuarios_dict
    except aiosqlite.Error as e:
        print(f"[ERROR] Error al obtener usuarios de la base de datos: {e}")
        return {}

async def save_user(chat_id, nombre):
    try:
        async with aiosqlite.connect('usuarios_telegram.db') as conn:
            async with conn.execute("SELECT * FROM usuarios WHERE chat_id = ?", (chat_id,)) as cursor:
                user = await cursor.fetchone()
                if not user:
                    current_time = datetime.now().isoformat()
                    # *** CÓDIGO CORREGIDO ***
                    await conn.execute("INSERT INTO usuarios (chat_id, nombre, suscripciones, suscripcion_fecha, fecha_ultima_actividad) VALUES (?, ?, ?, ?, ?)", (chat_id, nombre, '', current_time, current_time))
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
                suscripciones = suscripciones_db[0].split(',') if suscripciones_db and suscripciones_db[0] else []
    except aiosqlite.Error as e:
        print(f"[ERROR] Error al obtener las suscripciones del usuario: {e}")
        return

    keyboard = []
    temporalidades = ['15m', '1h', '4h', '1d']
    for temporalidad in temporalidades:
        button_text = f"{'Desuscribirse' if temporalidad in suscripciones else 'Suscribirse'} {temporalidad}"
        callback_data = f"{'desuscribir' if temporalidad in suscripciones else 'suscribir'}_{temporalidad}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # *** SOLUCIÓN CLAVE: Editar con un texto diferente (invisible) ***
    try:
        await update.callback_query.edit_message_text(
            text="Actualizando suscripciones...",  # Texto temporal
            reply_markup=reply_markup
        )
    except telegram.error.BadRequest as e:
        if str(e).startswith("Message is not modified"):
            # Si no hay cambios reales, enviar un mensaje diferente
            await update.callback_query.answer("No hay cambios en tus suscripciones.")
        else:
            print(f"Error al editar mensaje: {e}")

async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat.id
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


def check_initial_reports():
    temporalidades = ['15m', '1h', '4h', '1d']
    os.makedirs(reports_dir, exist_ok=True)
    for temporalidad in temporalidades:
        report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
        if not os.path.exists(report_path):
            raise FileNotFoundError(f"El archivo de informe para la temporalidad '{temporalidad}' no existe.")


async def send_report(chat_id, temporalidad, bot, latest_closing_time): #Recibe el ultimo cierre
    """Envía un informe al usuario si está actualizado con respecto al cierre de la vela."""
    global last_checked
    report_path = os.path.join(reports_dir, f"report_{temporalidad}.md")
    
    if not os.path.exists(report_path):
        print(f"[WARNING] Informe de {temporalidad} no encontrado para chat_id: {chat_id}.")
        return
    
    closing_timestamp = latest_closing_time.timestamp()

    # Verificar la última modificación del archivo
    last_modified = os.path.getmtime(report_path)
    last_reviewed = last_checked.get(report_path, 0)

    # Si el archivo no está actualizado según el cierre de vela, tomar acción
    if last_modified <= closing_timestamp:
        if temporalidad == '15m':
            print(f"[INFO] Informe de 15m no actualizado, intentando actualizar cada 15 segundos durante 90 segundos para chat_id: {chat_id}.")
            for _ in range(6):  # Intentar 6 veces con intervalos de 15 segundos (6 x 15 = 90)
                await asyncio.sleep(15)
                last_modified = os.path.getmtime(report_path)
                if last_modified > closing_timestamp:
                    break  # Salir del bucle si el archivo se actualiza
            else:
                print(f"[WARNING] Informe de 15m no actualizado tras 90 segundos, pasando al siguiente.")
                return  # Salir si no se actualizó tras los 90 segundos
        else:
            print(f"[INFO] Informe de {temporalidad} no actualizado, pasando al siguiente.")
            return  # Salir para otras temporalidades si no está actualizado

    # Leer y enviar el informe si está actualizado
    with open(report_path, 'r') as file:
        report_content = file.read()
    try:
        await bot.send_message(chat_id=chat_id, text=report_content)
        print(f"[INFO] Informe de {temporalidad} enviado a chat_id: {chat_id}.")
        last_checked[report_path] = last_modified  # Actualizar el registro de revisión
    except Exception as e:
        print(f"[ERROR] Error al enviar mensaje a {chat_id}: {e}")

async def check_and_send_reports(chat_id, suscripciones, bot, latest_closing_times): #Recibe el diccionario de ultimos cierres
    for temporalidad in ['1d', '4h', '1h', '15m']:
        if temporalidad in suscripciones:
            await send_report(chat_id, temporalidad, bot, latest_closing_times[temporalidad]) #Pasa el ultimo cierre correspondiente

async def send_reports_to_all_users(bot, latest_closing_times): #Recibe el diccionario de ultimos cierres
    all_subscriptions = await get_all_user_subscriptions()
    for chat_id, suscripciones in all_subscriptions.items():
        await check_and_send_reports(chat_id, suscripciones, bot, latest_closing_times)

async def handle_candle_closure(bot):
    """Controla el ciclo principal."""
    while True:
        try:
            # Definir start_time *dentro* del bucle
            start_time = time.time() #Definicion correcta

            current_time = datetime.now()

            closing_times = {}
            # Se itera sobre las temporalidades
            for timeframe in ['1d', '4h', '1h', '15m']:
                # Se llama a get_closing_time() para obtener el *próximo* cierre
                # y se almacena en el diccionario con la temporalidad como clave
                closing_times[timeframe] = get_closing_time(timeframe)

            proximo_cierre_15m = closing_times["15m"]
            tiempo_espera = (proximo_cierre_15m - current_time).total_seconds()

            if tiempo_espera > 0:
                print(f"[INFO] Esperando {tiempo_espera:.0f} segundos hasta el próximo cierre de 15m: {proximo_cierre_15m}")
                await asyncio.sleep(tiempo_espera)
            else:
                print("El analisis tardo mas de 15 minutos. Iniciando ciclo inmediatamente...")

            print(f"Iniciando ciclo de análisis: {datetime.now()}")

            # Se pasa el diccionario closing_times a las funciones de envío de reportes
            await send_reports_to_all_users(bot, closing_times)

            print(f"[INFO] Tiempo transcurrido en todo el ciclo: {(time.time() - start_time):.2f} segundos.")

        except Exception as e:
            print(f"[ERROR] Error en el ciclo principal: {e}")
            await asyncio.sleep(60)


def get_closing_time(temporalidad): #Ahora calcula el proximo cierre
    """Calcula el *próximo* tiempo de cierre de la vela para la temporalidad dada."""
    current_time = datetime.now()

    if temporalidad == '15m':
        minute_offset = current_time.minute % 15
        closing_time = current_time + timedelta(minutes=15 - minute_offset)
    elif temporalidad == '1h':
        closing_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    elif temporalidad == '4h':
        hour_offset = current_time.hour % 4
        closing_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=4 - hour_offset)
    elif temporalidad == '1d':
        closing_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        raise ValueError(f"Temporalidad no válida: {temporalidad}")

    return closing_time.replace(second=0, microsecond=0)

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

async def initialize():
    """Configura la base de datos y verifica reportes iniciales."""
    print("[INFO] Configurando la base de datos y reportes iniciales...")
    await create_db()  # Debe ser asincrónico
    check_initial_reports()

def setup_handlers(application):
    """Configura los handlers del bot."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_temporalidades, pattern='^suscripcion$'))
    application.add_handler(CallbackQueryHandler(button))

async def start_bot(application):
    """Inicia el ciclo de vida del bot."""
    print("[INFO] Iniciando el bot...")
    await application.initialize()
    print("[DEBUG] Bot inicializado.")
    await application.start()
    print("[DEBUG] Bot iniciado.")
    await application.updater.start_polling()
    print("[DEBUG] Bot en polling.")
   

async def main():
    """Función principal."""
    print("[INFO] Configurando el bot...")

    # Paso 1: Inicialización
    await initialize()

    # Paso 2: Configuración del bot
    bot_token = os.getenv("TELEGRAM_TOKEN")
    if not bot_token:
        raise ValueError("El token del bot no está configurado.")

    application = ApplicationBuilder().token(bot_token).build()
    setup_handlers(application)

    # Paso 3: Ejecutar tareas concurrentes usando la base de datos

    usuarios = await obtener_usuarios_de_db()


    # Paso 4: Iniciar el bot
    await start_bot(application)


    if usuarios:
    # No necesitamos pasar chat_id ni suscripciones ahora
        print(f"Creando tarea para manejar el cierre de velas para todos los usuarios.")
        asyncio.create_task(handle_candle_closure(application.bot))

    # Esperar a que todas las tareas se ejecuten
        await asyncio.gather(*asyncio.all_tasks())
    else:
        print("[INFO] No hay usuarios en la base de datos.")

if __name__ == "__main__":
    asyncio.run(main())
   
