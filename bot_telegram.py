from telegram.ext import Application, CommandHandler

async def start(update, context):
    await update.message.reply("¡Hola! Soy un bot de prueba.")

async def main():
    # Inicializa la aplicación con tu token
    application = Application.builder().token("YOUR_BOT_TOKEN").build()

    # Añadir un manejador para el comando /start
    application.add_handler(CommandHandler("start", start))

    # Inicia el polling para escuchar actualizaciones
    await application.run_polling()

if __name__ == "__main__":
    # Simplemente ejecutamos la función principal sin asyncio.run()
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())
