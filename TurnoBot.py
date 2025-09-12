import discord
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
import pytz
import os

# 🔹 Configurar intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Diccionario para guardar las horas de inicio por usuario
turnos = {}

# Zona horaria España
zona = pytz.timezone("Europe/Madrid")

# Diccionario con precios de los tuneos
precios_tuneos = {
    "Frenos": 80000,
    "Motor": 80000,
    "Suspensión": 80000,
    "Transmisión": 80000,
    "Blindaje": 105000,
    "Turbo": 100000,
    "Full tuning con blindaje": 525000,
    "Full tuning sin blindaje": 450000,
    "Cambio estético": 20000,
    "Reparación en el taller": 10000,
    "Reparación en la calle": 15000,
    "Kit de reparación": 50000
}

# Diccionario para registrar tuneos por usuario
usuarios_tuneos = {}

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# Comando de prueba
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

# Comando de turnos
@bot.command()
async def turno(ctx):
    """Comando para enviar el botón de turno"""
    button = Button(label="⏱️ Iniciar / Finalizar turno", style=discord.ButtonStyle.green)

    async def button_callback(interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now(zona)

        if user_id not in turnos:
            turnos[user_id] = now
            await interaction.response.send_message(
                f"🔧 {interaction.user.mention} ha iniciado su turno a las **{now.strftime('%H:%M:%S')}**",
                ephemeral=False
            )
        else:
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

# Comando para iniciar el menú de tuneos
@bot.command()
async def tuning(ctx):
    """Envía botones para cada tuneo disponible"""
    view = View()
    
    for tuneo, precio in precios_tuneos.items():
        button = Button(label=f"{tuneo} (${precio})", style=discord.ButtonStyle.blurple)

        async def tuneo_callback(interaction: discord.Interaction, t=tuneo, p=precio):
            user_id = interaction.user.id
            if user_id not in usuarios_tuneos:
                usuarios_tuneos[user_id] = {}
            if t not in usuarios_tuneos[user_id]:
                usuarios_tuneos[user_id][t] = 0
            usuarios_tuneos[user_id][t] += 1

            total = sum(cantidad * precios_tuneos[nombre] for nombre, cantidad in usuarios_tuneos[user_id].items())

            await interaction.response.send_message(
                f"🔧 {interaction.user.mention} realizó {t}.\n"
                f"💰 Total acumulado: ${total:,}",
                ephemeral=False
            )

        button.callback = tuneo_callback
        view.add_item(button)

    await ctx.send("Selecciona el tuneo que deseas realizar:", view=view)

# Comando para ver el historial de tuneos de un usuario
@bot.command()
async def mis_tuneos(ctx):
    user_id = ctx.author.id
    if user_id not in usuarios_tuneos or not usuarios_tuneos[user_id]:
        await ctx.send(f"❌ {ctx.author.mention}, no tienes tuneos realizados.")
        return

    msg = f"🔧 {ctx.author.mention}, tus tuneos:\n"
    total = 0
    for t, cantidad in usuarios_tuneos[user_id].items():
        subtotal = cantidad * precios_tuneos[t]
        total += subtotal
        msg += f"- {t}: {cantidad} (${subtotal:,})\n"
    msg += f"💰 Total acumulado: ${total:,}"
    await ctx.send(msg)

# Arrancar el bot
bot.run(os.getenv("DISCORD_TOKEN"))
