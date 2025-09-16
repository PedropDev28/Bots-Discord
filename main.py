import os
import discord
from discord.ext import commands

from config.settings import INTENTS, PREFIX
from handlers.commands import register_commands
from tasks.periodic import start_tasks
from views.ui_components import setup_views
from utils.helpers import enviar_anuncio
from config.constants import CANAL_IDENTIFICACION


def create_bot() -> commands.Bot:
    bot = commands.Bot(command_prefix=PREFIX, intents=INTENTS)
    # Desactivar help por defecto para usar uno personalizado
    try:
        bot.remove_command("help")
    except Exception:
        pass

    @bot.event
    async def on_ready():
        print(f"Bot conectado como {bot.user}")

        # Iniciar tareas periódicas
        try:
            start_tasks(bot)
        except Exception:
            pass

        # Enviar anuncio inicial
        try:
            await enviar_anuncio(bot)
        except Exception:
            pass

        # Construir y enviar vistas/botones
        try:
            await setup_views(bot)
        except Exception:
            pass

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
        print("ERROR: La variable de entorno DISCORD_TOKEN no está configurada.")
    else:
        bot = create_bot()
        bot.run(TOKEN)
