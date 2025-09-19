import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging

# Cargar variables de entorno temprano (para que utils.supabase_service las pueda usar)
load_dotenv()

from config.settings import INTENTS, PREFIX
from handlers.commands import register_commands
from tasks.periodic import start_tasks
from views.ui_components import setup_views
from utils.helpers import enviar_anuncio
from config.constants import CANAL_IDENTIFICACION
from utils.supabase_service import supabase_service

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_bot() -> commands.Bot:
    bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)
    # Desactivar help por defecto para usar uno personalizado
    try:
        bot.remove_command("help")
    except Exception:
        pass

    @bot.event
    async def on_ready():
        logger.info(f"Bot conectado como {bot.user}")

        # Probar conexión con Supabase
        try:
            connection_ok = await supabase_service.test_connection()
            if connection_ok:
                logger.info("✅ Supabase connection established")
            else:
                logger.warning("❌ Supabase connection failed")
        except Exception as e:
            logger.exception("❌ Supabase error on_ready: %s", e)

        # Iniciar tareas periódicas
        try:
            start_tasks(bot)
        except Exception:
            logger.exception("Error starting periodic tasks")

        # Enviar anuncio inicial
        try:
            await enviar_anuncio(bot)
        except Exception:
            logger.exception("Error sending initial announcement")

        # Construir y enviar vistas/botones
        try:
            await setup_views(bot)
        except Exception:
            logger.exception("Error setting up UI views")

    @bot.event
    async def on_message(message: discord.Message):
        # Evitar reaccionar a otros bots
        if message.author.bot:
            return
        # Borrar mensajes escritos en el canal de identificación
        try:
            if message.channel.id == CANAL_IDENTIFICACION:
                await message.delete()
                return
        except Exception:
            pass
        await bot.process_commands(message)

    # Registrar comandos
    register_commands(bot)
    return bot


if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        logger.error("ERROR: La variable de entorno DISCORD_TOKEN no está configurada.")
    else:
        bot = create_bot()
        bot.run(TOKEN)
