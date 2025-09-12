import discord
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
import pytz
import os

# 🔹 Configurar intents
intents = discord.Intents.default()
intents.message_content = True  # Para leer mensajes en servidores
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Diccionario para guardar las horas de inicio por usuario
turnos = {}

# Zona horaria España
zona = pytz.timezone("Europe/Madrid")

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# Comando de prueba rápido
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

@bot.command()
async def turno(ctx):
    """Comando para enviar el botón de turno"""
    button = Button(label="⏱️ Iniciar / Finalizar turno", style=discord.ButtonStyle.green)

    async def button_callback(interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now(zona)  # Hora correcta en España

        if user_id not in turnos:
            # Si no tiene turno, lo inicia
            turnos[user_id] = now
            await interaction.response.send_message(
                f"🔧 {interaction.user.mention} ha iniciado su turno a las **{now.strftime('%H:%M:%S')}**",
                ephemeral=False
            )
        else:
            # Si ya tenía turno, lo finaliza y calcula la diferencia
            inicio = turnos.pop(user_id)
            diff = now - inicio
            horas, resto = divmod(diff.total_seconds(), 3600)
            minutos, segundos = divmod(resto, 60)
            await interaction.response.send_message(
                f"✅ {interaction.user.mention} ha finalizado su turno.\n"
                f"⏰ Duración: {int(horas)}h {int(minutos)}m {int(segundos)}s",
                ephemeral=False
            )

    button.callback = button_callback
    view = View()
    view.add_item(button)
    await ctx.send("Pulsa el botón para iniciar/finalizar tu turno:", view=view)

# Arrancar el bot usando la variable de entorno
bot.run(os.getenv("DISCORD_TOKEN"))
