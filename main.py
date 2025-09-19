import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
from datetime import datetime

# Cargar variables de entorno temprano (para que utils.supabase_service las pueda usar)
load_dotenv()

from config.settings import INTENTS, PREFIX
from handlers.commands import register_commands
from tasks.periodic import start_tasks
from views.ui_components import setup_views
from utils.helpers import enviar_anuncio, safe_get_channel
from config.constants import CANAL_IDENTIFICACION, CANAL_LOGS
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

    # Nuevo: registrar abandono de miembros
    @bot.event
    async def on_member_remove(member: discord.Member):
        """
        Log cuando un usuario abandona el servidor:
        - Enviar embed al canal de logs (CANAL_LOGS)
        - Añadir entrada sencilla en leaves.log en la raíz del proyecto
        """
        try:
            logger.info(f"Miembro salido: {member} ({member.id})")
            # Construir embed
            embed = discord.Embed(
                title="👋 Usuario abandonó el servidor",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow(),
            )
            embed.add_field(name="Usuario", value=f"{member} ({member.id})", inline=False)
            try:
                embed.add_field(name="Cuenta creada", value=member.created_at.isoformat(), inline=True)
            except Exception:
                pass
            try:
                if member.joined_at:
                    embed.add_field(name="Se unió", value=member.joined_at.isoformat(), inline=True)
            except Exception:
                pass

            # Enviar al canal de logs si existe
            canal = None
            try:
                canal = safe_get_channel(bot, CANAL_LOGS) or bot.get_channel(CANAL_LOGS)
            except Exception:
                canal = bot.get_channel(CANAL_LOGS) if CANAL_LOGS else None

            if canal:
                try:
                    await canal.send(embed=embed)
                except Exception:
                    logger.exception("No se pudo enviar el mensaje de salida al canal de logs")

            # Añadir registro local
            try:
                root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                log_path = os.path.join(root, "leaves.log")
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.utcnow().isoformat()} | {member} | {member.id}\n")
            except Exception:
                logger.exception("No se pudo escribir en leaves.log")
        except Exception:
            logger.exception("Error en on_member_remove")

    # Registrar comandos
    register_commands(bot)

    # Cargar cogs que exponen comandos (ej. admin_commands con test_supabase / migrate_backup)
    try:
        bot.load_extension("handlers.admin_commands")
        logger.info("Cog handlers.admin_commands cargado correctamente")
    except Exception as e:
        logger.exception("No se pudo cargar handlers.admin_commands: %s", e)

    return bot


if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        logger.error("ERROR: La variable de entorno DISCORD_TOKEN no está configurada.")
    else:
        bot = create_bot()
        bot.run(TOKEN)
