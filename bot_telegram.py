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
    # Deja que Application maneje el ciclo de eventos internamente
    import asyncio
    asyncio.run(main())  # Solo usa asyncio.run() para llamar a main()
