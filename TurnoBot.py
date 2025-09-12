import discord
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
import pytz
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

zona = pytz.timezone("Europe/Madrid")

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

# Roles permitidos por ID
ROLES_TUNEO = [1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425, 1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423, 1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882, 1391019755267424347, 1385301435456950391, 1385301435456950390, 1415954460202766386 ]  # IDs de roles que pueden iniciar tuneo
ROLES_HISTORIAL_TOTAL = [1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425, 1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423, 1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882, 1415954460202766386]  # IDs de staff / propietario


# Turnos activos: user_id -> {"dinero": total_dinero_en_turno}
turnos_tuneo = {}

# Historial completo: user_id -> {"dinero": total_dinero_acumulado, "tuneos": total_tuneos_completos}
historial_tuneos = {}

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# Iniciar turno
@bot.command()
async def iniciar_tuneo(ctx):
    if not any(role.id in ROLES_TUNEO for role in ctx.author.roles):
        await ctx.send("❌ No tienes permiso para iniciar un tuneo.", ephemeral=True)
        return

    uid = ctx.author.id
    if uid in turnos_tuneo:
        await ctx.send(f"❌ {ctx.author.mention}, ya tienes un turno activo.", ephemeral=True)
        return

    turnos_tuneo[uid] = {"dinero": 0}
    view = View()

    # Botones para cada parte del tuneo
    for tuneo, precio in precios_tuneos.items():
        button = Button(label=f"{tuneo} (${precio:,})", style=discord.ButtonStyle.blurple)

        async def tuneo_callback(interaction: discord.Interaction, t=tuneo, p=precio):
            uid2 = interaction.user.id
            if uid2 not in turnos_tuneo:
                await interaction.response.send_message("❌ No tienes un turno activo.", ephemeral=True)
                return

            turnos_tuneo[uid2]["dinero"] += p
            total_dinero = turnos_tuneo[uid2]["dinero"]

            await interaction.response.send_message(
                f"🔧 Añadido {t} a tu turno.\n💰 Total acumulado: ${total_dinero:,}",
                ephemeral=True
            )

        button.callback = tuneo_callback
        view.add_item(button)

    # Botón finalizar turno
    finalizar = Button(label="✅ Finalizar tuneo", style=discord.ButtonStyle.green)

    async def finalizar_callback(interaction: discord.Interaction):
        uid2 = interaction.user.id
        if uid2 not in turnos_tuneo:
            await interaction.response.send_message("❌ No tienes un turno activo.", ephemeral=True)
            return

        total_dinero = turnos_tuneo[uid2].pop("dinero")
        turnos_tuneo.pop(uid2)

        if uid2 not in historial_tuneos:
            historial_tuneos[uid2] = {"dinero": 0, "tuneos": 0}

        historial_tuneos[uid2]["dinero"] += total_dinero
        historial_tuneos[uid2]["tuneos"] += 1  # Un solo tuneo completo

        await interaction.response.send_message(
            f"✅ Turno finalizado.\n💰 Total de dinero de este turno: ${total_dinero:,}\n🎯 Tuneo completo registrado: 1",
            ephemeral=True
        )

    finalizar.callback = finalizar_callback
    view.add_item(finalizar)

    await ctx.send(f"{ctx.author.mention}, tu turno de tuneo ha comenzado. Pulsa los botones:", view=view)

# Historial personal (dinero acumulado)
@bot.command()
async def mis_tuneos(ctx):
    uid = ctx.author.id
    total_dinero = historial_tuneos.get(uid, {}).get("dinero", 0)
    await ctx.send(f"💰 Has acumulado un total de ${total_dinero:,} en tuneos.", ephemeral=True)

# Historial total (solo roles permitidos, muestra tuneos completos)
@bot.command()
async def historial_total(ctx):
    if not any(role.id in ROLES_HISTORIAL_TOTAL for role in ctx.author.roles):
        await ctx.send("❌ No tienes permiso para ver el historial completo.", ephemeral=True)
        return

    if not historial_tuneos:
        await ctx.send("❌ No hay tuneos registrados aún.", ephemeral=True)
        return

    msg = "📋 Historial completo de tuneos:\n"
    for uid, datos in historial_tuneos.items():
        user = ctx.guild.get_member(uid)
        nombre = user.display_name if user else f"ID:{uid}"
        total_tuneos = datos.get("tuneos", 0)
        msg += f"- {nombre}: {total_tuneos} tuneos\n"

    await ctx.send(msg, ephemeral=True)

bot.run(os.getenv("DISCORD_TOKEN"))
