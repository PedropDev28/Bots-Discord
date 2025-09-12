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

# Turnos de tuneo activos: user_id -> {tuneo: cantidad}
turnos_tuneo = {}

# Historial general: user_id -> {tuneo: cantidad total}
historial_tuneos = {}

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# Comando de prueba
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

# Comando para iniciar un turno de tuneo
@bot.command()
async def iniciar_tuneo(ctx):
    user_id = ctx.author.id
    if user_id in turnos_tuneo:
        await ctx.send(f"❌ {ctx.author.mention}, ya tienes un turno de tuneo activo.")
        return

    turnos_tuneo[user_id] = {}
    view = View()

    # Botones para cada tuneo
    for tuneo, precio in precios_tuneos.items():
        button = Button(label=f"{tuneo} (${precio:,})", style=discord.ButtonStyle.blurple)

        async def tuneo_callback(interaction: discord.Interaction, t=tuneo, p=precio):
            uid = interaction.user.id
            if uid not in turnos_tuneo:
                await interaction.response.send_message("❌ No tienes un turno activo. Usa !iniciar_tuneo", ephemeral=True)
                return

            turno_actual = turnos_tuneo[uid]
            if t not in turno_actual:
                turno_actual[t] = 0
            turno_actual[t] += 1

            total_turno = sum(cantidad * precios_tuneos[nombre] for nombre, cantidad in turno_actual.items())
            await interaction.response.send_message(
                f"🔧 {interaction.user.mention} añadió {t} a su turno.\n"
                f"💰 Total acumulado en este turno: ${total_turno:,}",
                ephemeral=False
            )

        button.callback = tuneo_callback
        view.add_item(button)

    # Botón para finalizar el turno
    finalizar = Button(label="✅ Finalizar tuneo", style=discord.ButtonStyle.green)

    async def finalizar_callback(interaction: discord.Interaction):
        uid = interaction.user.id
        if uid not in turnos_tuneo:
            await interaction.response.send_message("❌ No tienes un turno activo.", ephemeral=True)
            return

        turno_actual = turnos_tuneo.pop(uid)
        if uid not in historial_tuneos:
            historial_tuneos[uid] = {}

        for t, cantidad in turno_actual.items():
            if t not in historial_tuneos[uid]:
                historial_tuneos[uid][t] = 0
            historial_tuneos[uid][t] += cantidad

        total_final = sum(cantidad * precios_tuneos[nombre] for nombre, cantidad in turno_actual.items())
        await interaction.response.send_message(
            f"✅ {interaction.user.mention} ha finalizado su turno de tuneo.\n"
            f"💰 Total de este turno: ${total_final:,}",
            ephemeral=False
        )

    finalizar.callback = finalizar_callback
    view.add_item(finalizar)

    await ctx.send(f"{ctx.author.mention}, tu turno de tuneo ha comenzado. Pulsa los botones para agregar tuneos:", view=view)

# Comando para ver tu historial de tuneos
@bot.command()
async def historial(ctx):
    user_id = ctx.author.id
    if user_id not in historial_tuneos or not historial_tuneos[user_id]:
        await ctx.send(f"❌ {ctx.author.mention}, no tienes tuneos realizados.")
        return

    msg = f"🔧 {ctx.author.mention}, historial de tus tuneos:\n"
    total = 0
    for t, cantidad in historial_tuneos[user_id].items():
        subtotal = cantidad * precios_tuneos[t]
        total += subtotal
        msg += f"- {t}: {cantidad} (${subtotal:,})\n"
    msg += f"💰 Total acumulado en todos tus tuneos: ${total:,}"
    await ctx.send(msg)

# Arrancar el bot
bot.run(os.getenv("DISCORD_TOKEN"))
