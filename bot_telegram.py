import os
import logging
import sqlite3
import markdown
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, Application, MessageHandler, filters
from telegram.constants import ParseMode
import asyncio

# Configuració
DATABASE_FILE = "usuarios.db"
RUTA_INFORMES = "Informe Final"
ultima_modificacion_guardada = {}
MAX_REINTENTOS_15M = 8  # Máximo 8 reintentos
INTERVALO_REINTENTO_15M = 15 * 60  # 15 minutos en segundos

# Configuración del logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token del bot (usando variable de entorno)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    logger.error("Error: No se ha encontrado el token del bot. Define la variable de entorno TELEGRAM_BOT_TOKEN.")
    exit(1)
# Función para enviar informes periódicamente

async def enviar_informe(context: ContextTypes.DEFAULT_TYPE, temporalidad):
    bot = context.bot
    nombre_archivo = f"report_{temporalidad}.md"
    ruta_archivo = os.path.join(RUTA_INFORMES, nombre_archivo)
    if os.path.exists(ruta_archivo):
        try:
            with open(ruta_archivo, "r", encoding="utf-8") as archivo:
                contenido_informe = archivo.read()
                html = markdown.markdown(contenido_informe)
                usuarios = obtener_usuarios_suscritos(temporalidad)
                for usuario in usuarios:
                    try:
                        await bot.send_message(chat_id=usuario[0], text=html, parse_mode=ParseMode.HTML)
                        logger.info(f"Informe {temporalidad} enviado a {usuario[0]}")
                    except telegram.error.TelegramError as e:
                        logger.error(f"Error al enviar mensaje a {usuario[0]}: {e}")
        except FileNotFoundError:
            logger.error(f"Archivo no encontrado: {ruta_archivo}")
        except Exception as e:
            logger.error(f"Error al procesar {ruta_archivo}: {e}")
    else:
        logger.warning(f"No existe el archivo {ruta_archivo}")


# Función para obtener los usuarios suscritos a una temporalidad
def obtener_usuarios_suscritos(temporalidad):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM usuarios WHERE ? IN (temporalidades_suscritas)", (temporalidad,))
        usuarios = cursor.fetchall()
        return usuarios
    except sqlite3.Error as e:
        logger.error(f"Error al obtener usuarios suscritos: {e}")
        return []
    finally:
        conn.close()
    pass
    
async def revisar_informe_15m(context: ContextTypes.DEFAULT_TYPE):
    ruta_archivo = os.path.join(RUTA_INFORMES, "report_15m.md")
    if not os.path.exists(ruta_archivo):
        return

    ultima_modificacion = os.path.getmtime(ruta_archivo)

    if ultima_modificacion > ultima_modificacion_guardada.get("report_15m.md", 0):
        ultima_modificacion_guardada["report_15m.md"] = ultima_modificacion
        await enviar_informe(context, "15m")
        context.job.data["reintentos"] = 0 #Reiniciar reintentos despues de enviar el informe
        return
    elif context.job.data["reintentos"] < MAX_REINTENTOS_15M:
        context.job.data["reintentos"] += 1
        logger.info(f"Reintento {context.job.data['reintentos']} para report_15m.md")
    else:
        logger.info("Máximo de reintentos alcanzado para report_15m.md.")
        context.job.data["reintentos"] = 0 #Reiniciar reintentos
        return


async def revisar_otros_informes(context: ContextTypes.DEFAULT_TYPE):
    #Lógica para revisar otros informes (1h, 4h, 1d, etc.)
    pass

async def revisar_informes(context: ContextTypes.DEFAULT_TYPE):
    await revisar_informe_15m(context)
    await revisar_otros_informes(context)

# Función para crear la tabla de usuarios
def crear_tabla_usuarios():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                user_id INTEGER PRIMARY KEY,
                temporalidades_suscritas TEXT DEFAULT '15m,1h,4h,1d',
                fecha_inicio_suscripcion TEXT,
                estado_suscripcion TEXT DEFAULT 'gratis'
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error al crear la tabla usuarios: {e}")
    finally:
        conn.close()

async def echo(update, context):
    user_message = update.message.text
    await update.message.reply_text(f"Dijiste: {user_message}")


# Comando /suscribir para agregar una temporalidad
def suscribir(update, context):
    user_id = update.effective_user.id
    if context.args:
        temporalidad = context.args[0]
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT temporalidades_suscritas FROM usuarios WHERE user_id=?", (user_id,))
        resultado = cursor.fetchone()
        if resultado:
            temporalidades = resultado[0].split(',')
            if temporalidad not in temporalidades:
                temporalidades.append(temporalidad)
                cursor.execute("UPDATE usuarios SET temporalidades_suscritas=? WHERE user_id=?", (','.join(temporalidades), user_id))
                conn.commit()
                update.message.reply_text(f"Suscrito a {temporalidad}")
            else:
                update.message.reply_text(f"Ya estas suscrito a {temporalidad}")
        else:
            cursor.execute("INSERT INTO usuarios (user_id, temporalidades_suscritas) VALUES (?, ?)", (user_id, temporalidad))
            conn.commit()
            update.message.reply_text(f"Suscrito a {temporalidad}")
        conn.close()
    else:
        update.message.reply_text("Usa /suscribir <temporalidad>. Ejemplo: /suscribir 1h")

# Comando /desuscribir para eliminar una temporalidad
def desuscribir(update, context):
    user_id = update.effective_user.id
    if context.args:
        temporalidad = context.args[0]
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT temporalidades_suscritas FROM usuarios WHERE user_id=?", (user_id,))
        resultado = cursor.fetchone()
        if resultado:
            temporalidades = resultado[0].split(',')
            if temporalidad in temporalidades:
                temporalidades.remove(temporalidad)
                cursor.execute("UPDATE usuarios SET temporalidades_suscritas=? WHERE user_id=?", (','.join(temporalidades), user_id))
                conn.commit()
                update.message.reply_text(f"Desuscrito de {temporalidad}")
            else:
                update.message.reply_text(f"No estas suscrito a {temporalidad}")
        conn.close()
    else:
        update.message.reply_text("Usa /desuscribir <temporalidad>. Ejemplo: /desuscribir 1h")

# Comando /start para iniciar el bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    crear_tabla_usuarios()
    if "revisar_informes" not in context.job_queue.jobs():
        context.job_queue.run_repeating(
            revisar_informes,
            interval=INTERVALO_REINTENTO_15M,
            first=INTERVALO_REINTENTO_15M,
            name="revisar_informes",
            data={"reintentos": 0}
        )
        await update.message.reply_text("¡Hola! Bot iniciado y programado para revisar informes.")
    else:
        await update.message.reply_text("El bot ya está programado para revisar informes.")
# Función para mostrar los botones de temporalidades

async def mostrar_botones_temporalidades(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT temporalidades_suscritas FROM usuarios WHERE user_id=?", (user_id,))
        resultado = cursor.fetchone()
        temporalidades_suscritas = resultado[0].split(',') if resultado else []
        keyboard = []
        for temporalidad in ["15m", "1h", "4h", "1d"]:
            texto_boton = f"Desactivar {temporalidad}" if temporalidad in temporalidades_suscritas else f"Activar {temporalidad}"
            keyboard.append([InlineKeyboardButton(texto_boton, callback_data=temporalidad)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)
        except telegram.error.BadRequest:
            await update.callback_query.message.reply_text("Temporalidades:", reply_markup=reply_markup)
    except sqlite3.Error as e:
        logger.error(f"Error al obtener las suscripciones del usuario: {e}")
    finally:
        conn.close()

# Función para gestionar los botones interactivos
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  
    user_id = query.from_user.id
    data = query.data

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        if data == 'suscribir_todo':
            cursor.execute("INSERT OR REPLACE INTO usuarios (user_id, temporalidades_suscritas) VALUES (?, ?)", (user_id, '15m,1h,4h,1d'))
        else:
            cursor.execute("SELECT temporalidades_suscritas FROM usuarios WHERE user_id=?", (user_id,))
            resultado = cursor.fetchone()
            temporalidades = resultado[0].split(',') if resultado else []

            if data in temporalidades:
                temporalidades.remove(data)
            else:
                temporalidades.append(data)

            cursor.execute("UPDATE usuarios SET temporalidades_suscritas=? WHERE user_id=?", (','.join(temporalidades), user_id))
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error al interactuar con la base de datos: {e}")
    finally:
        conn.close()
    await mostrar_botones_temporalidades(update, context, user_id)

# Comando para ver las suscripciones
def lista_suscripciones(update, context):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT temporalidades_suscritas FROM usuarios WHERE user_id=?", (user_id,))
        resultado = cursor.fetchone()
        if resultado:
            update.message.reply_text(f"Estás suscrito a: {resultado[0]}")
        else:
            update.message.reply_text("No estás suscrito a ninguna temporalidad.")
    except sqlite3.Error as e:
        logger.error(f"Error al obtener la lista de suscripciones: {e}")
    finally:
        conn.close()

# Función principal para configurar el bot
async def main():
    # Leer el token del entorno
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        logger.error("El token de Telegram no está configurado en las variables de entorno.")
        raise ValueError("El token de Telegram no está configurado en las variables de entorno.")

    # Crear la aplicación del bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Agregar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Ejecutar el bot con polling
    try:
        logger.info("El bot está iniciando...")
        await application.run_polling()
    except Exception as e:
        logger.exception("Error ejecutando el bot: %s", e)

# Punto de entrada del script
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "This event loop is already running" in str(e):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            logger.exception("Error crítico en el bucle principal: %s", e)
            raise

