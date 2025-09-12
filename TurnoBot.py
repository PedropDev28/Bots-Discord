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

zona = pytz.timezone("Europe/Madrid")

precios_tuneos = {
    "Frenos": 80000,
    "Neón": 80000,
    "Xenón": 80000,
    "Motor": 80000,
    "Faldones": 80000,
    "Vidrios": 80000,
    "Suspensión": 80000,
    "Transmisión": 80000,
    "Matrícula": 105000,
    "Capó": 105000,
    "Blindaje": 105000,
    "Color perlado": 105000,
    "Turbo": 100000,
    "Full tuning con blindaje": 525000,
    "Full tuning sin blindaje": 450000,
    "Cambio estético": 20000
}

# Turnos activos
turnos_tuneo = {}

# Historial completo: user_id -> {tuneo: cantidad}
historial_tuneos = {}

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# Comando para iniciar turno de tuneo (solo mecánicos)
@bot.command()
@commands.has_role("Mecánico")
async def iniciar_tuneo(ctx):
    user_id = ctx.author.id
    if user_id in turnos_tuneo:
        await ctx.send(f"❌ {ctx.author.mention}, ya tienes un turno activo.", ephemeral=True)
        return

    turnos_tuneo[user_id] = {}
    view = View()

    # Botones para cada tuneo
    for tuneo, precio in precios_tuneos.items():
        button = Button(label=f"{tuneo} (${precio:,})", style=discord.ButtonStyle.blurple)

        async def tuneo_callback(interaction: discord.Interaction, t=tuneo, p=precio):
            uid = interaction.user.id
            if uid not in turnos_tuneo:
                await interaction.response.send_message("❌ No tienes un turno activo.", ephemeral=True)
                return

            turno_actual = turnos_tuneo[uid]
            if t not in turno_actual:
                turno_actual[t] = 0
            turno_actual[t] += 1

            total_turno = sum(cantidad * precios_tuneos[nombre] for nombre, cantidad in turno_actual.items())
            await interaction.response.send_message(
                f"🔧 Añadido {t} a tu turno.\n💰 Total acumulado: ${total_turno:,}",
                ephemeral=True
            )

        button.callback = tuneo_callback
        view.add_item(button)

    # Botón finalizar turno
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
            f"✅ Turno finalizado.\n💰 Total de este turno: ${total_final:,}",
            ephemeral=True
        )

    finalizar.callback = finalizar_callback
    view.add_item(finalizar)

    await ctx.send(f"{ctx.author.mention}, tu turno de tuneo ha comenzado. Pulsa los botones:", view=view)

# Historial personal
@bot.command()
async def mis_tuneos(ctx):
    user_id = ctx.author.id
    if user_id not in historial_tuneos or not historial_tuneos[user_id]:
        await ctx.send(f"❌ No tienes tuneos realizados.", ephemeral=True)
        return

    msg = "🔧 Tus tuneos:\n"
    total = 0
    for t, cantidad in historial_tuneos[user_id].items():
        subtotal = cantidad * precios_tuneos[t]
        total += subtotal
        msg += f"- {t}: {cantidad} (${subtotal:,})\n"
    msg += f"💰 Total acumulado: ${total:,}"
    await ctx.send(msg, ephemeral=True)

# Historial total (solo administradores o rol específico)
@bot.command()
@commands.has_role("Jefe Taller")
async def historial_total(ctx):
    if not historial_tuneos:
        await ctx.send("❌ No hay tuneos registrados aún.", ephemeral=True)
        return

    msg = "📋 Historial completo de tuneos:\n"
    for uid, tuneos in historial_tuneos.items():
        user = ctx.guild.get_member(uid)
        nombre = user.display_name if user else f"ID:{uid}"
        total_usuario = sum(cantidad * precios_tuneos[t] for t, cantidad in tuneos.items())
        msg += f"\n🔹 {nombre} (Total: ${total_usuario:,})\n"
        for t, cantidad in tuneos.items():
            subtotal = cantidad * precios_tuneos[t]
            msg += f"   - {t}: {cantidad} (${subtotal:,})\n"

    await ctx.send(msg, ephemeral=True)

bot.run(os.getenv("DISCORD_TOKEN"))
