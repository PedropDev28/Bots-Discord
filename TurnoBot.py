import discord
from discord.ext import commands
from discord.ui import Button, View
import datetime
import os

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Diccionario para guardar las horas de inicio por usuario
turnos = {}

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

@bot.command()
async def turno(ctx):
    """Comando para enviar el botón de turno"""
    button = Button(label="⏱️ Iniciar / Finalizar turno", style=discord.ButtonStyle.green)

    async def button_callback(interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.datetime.now()

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

bot.run("DISCORD_TOKEN")
