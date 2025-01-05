import telegram
import os
import time
import schedule
import sqlite3
import markdown
import logging
import asyncio  # Importamos asyncio

from telegram import (
    Update,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

# Configuración
DATABASE_FILE = "usuarios.db"
TOKEN = "7465892171:AAGR8UyG6nFujlllAVHRi_UTlCAUEmwi0jU"  # ¡REEMPLAZA CON TU TOKEN REAL!
RUTA_INFORMES = "Informe Final"
ultima_modificacion_guardada = {}

# Configuración de logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
bot = telegram.Bot(token=TOKEN)

async def enviar_informes(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    for temporalidad in ["1d", "4h", "1h", "15m"]:
        nombre_archivo = f"report_{temporalidad}.md"
        ruta_archivo = os.path.join(RUTA_INFORMES, nombre_archivo)

        if os.path.exists(ruta_archivo):
            try:
                ultima_modificacion = os.path.getmtime(ruta_archivo)
                if ultima_modificacion > ultima_modificacion_guardada.get(nombre_archivo, 0):
                    ultima_modificacion_guardada[nombre_archivo] = ultima_modificacion
                    with open(ruta_archivo, "r", encoding="utf-8") as archivo:
                        contenido_informe = archivo.read()
                        html = markdown.markdown(contenido_informe)
                        usuarios = obtener_usuarios_suscritos(temporalidad)
                        for usuario in usuarios:
                            try:
                                await bot.send_message(chat_id=usuario[0], text=html, parse_mode=ParseMode.HTML)
                            except telegram.error.TelegramError as e:
                                logger.error(f"Error al enviar mensaje a {usuario[0]}: {e}")
                else:
                    logger.info(f"El archivo {ruta_archivo} no ha sido modificado.")

            except FileNotFoundError:
                logger.error(f"Archivo no encontrado: {ruta_archivo}")
            except Exception as e:
                logger.error(f"Error al procesar {ruta_archivo}: {e}")
        else:
            logger.warning(f"No existe el archivo {ruta_archivo}")




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


def suscribir(update, context):
    user_id = update.effective_user.id
    if context.args:
        temporalidad = context.args[0]
        conn = sqlite3.connect('usuarios.db')
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

def desuscribir(update, context):
    user_id = update.effective_user.id
    if context.args:
        temporalidad = context.args[0]
        conn = sqlite3.connect('usuarios.db')
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): #Se elimina la otra definicion de start
    crear_tabla_usuarios()
    keyboard = [[InlineKeyboardButton("Suscribirme a todo", callback_data='suscribir_todo')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "¡Bienvenido a BTCStream! Recibe informes de análisis técnico de Bitcoin.\n"
        "Presiona 'Suscribirme a todo' para comenzar a recibir informes de todas las temporalidades.\n"
        "Luego podrás desactivar las temporalidades que no te interesen.",
        reply_markup=reply_markup
    )


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
            keyboard.append([telegram.InlineKeyboardButton(texto_boton, callback_data=temporalidad)])
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)
        try:
            update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)
        except telegram.error.BadRequest:  # Captura la excepción BadRequest
             update.callback_query.message.reply_text("Temporalidades:", reply_markup=reply_markup) #envia un nuevo mensaje en caso de que el anterior ya no exista
    except sqlite3.Error as e:
        logger.error(f"Error al obtener las suscripciones del usuario: {e}")
    finally:
        conn.close()


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() #Eliminar el query.answer() duplicado
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
    await mostrar_botones_temporalidades(update, context, user_id) #Se agrega await

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
async def main():
    application = Application.builder().token(TOKEN).post_init(Application.initialize_job_queue).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("lista_suscripciones", lista_suscripciones))

    # Inicialización de la cola de trabajos
    application.initialize_job_queue()

    # Agregar un trabajo periódico
    application.job_queue.run_repeating(enviar_informes, interval=15 * 60, first=10)

    # Iniciar el bot
    await application.initialize()
    await application.start_polling()
    await application.idle()
