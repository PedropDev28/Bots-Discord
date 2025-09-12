import discord
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
import pytz
import os

# ------------------------------
# Configuración inicial
# ------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
zona = pytz.timezone("Europe/Madrid")

# Precios de los tuneos
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

# ------------------------------
# Roles por ID
# ------------------------------
ROLES_TUNEO = [1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425, 1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423, 1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882, 1391019755267424347, 1385301435456950391, 1385301435456950390, 1415954460202766386 ]  # IDs de roles que pueden iniciar tuneo
ROLES_HISTORIAL_TOTAL = [1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425, 1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423, 1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882, 1415954460202766386]  # IDs de staff / propietario

# ------------------------------
# Datos del bot
# ------------------------------
turnos_activos = {}      # user_id -> {"dinero": total_acumulado_en_turno}
tuneos_activos = {}      # user_id -> {"dinero": dinero_actual_del_tuneo}
historial_tuneos = {}    # user_id -> {"dinero_total": total_acumulado, "tuneos": total_tuneos_completos}

# ------------------------------
# Función de inicialización de mensajes fijos
# ------------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    # IDs de canales
    canal_turnos = bot.get_channel(1415949790545711236)  # Cambia por tu ID
    canal_tuneos = bot.get_channel(1415963375485321226)  # Cambia por tu ID
    canal_staff = bot.get_channel(1415964136550043689)   # Cambia por tu ID


    # --------------------------
    # Mensaje Turnos - Iniciar Turno
    # --------------------------
    view_turno = View()
    button_turno = Button(label="⏱️ Iniciar Turno", style=discord.ButtonStyle.green)

    async def iniciar_callback(interaction: discord.Interaction):
        uid = interaction.user.id
        await interaction.response.defer(ephemeral=True)

        if not any(role.id in ROLES_TUNEO for role in interaction.user.roles):
            await interaction.followup.send("❌ No tienes permiso para iniciar un turno.", ephemeral=True)
            return
        if uid in turnos_activos:
            await interaction.followup.send("❌ Ya tienes un turno activo.", ephemeral=True)
            return
        turnos_activos[uid] = {"dinero": 0}
        await interaction.followup.send("✅ Tu turno ha comenzado.", ephemeral=True)

    button_turno.callback = iniciar_callback
    view_turno.add_item(button_turno)

    # Botón finalizar turno
    button_finalizar_turno = Button(label="✅ Finalizar Turno", style=discord.ButtonStyle.red)

    async def finalizar_turno_callback(interaction: discord.Interaction):
        uid = interaction.user.id
        await interaction.response.defer(ephemeral=True)
        if uid not in turnos_activos:
            await interaction.followup.send("❌ No tienes un turno activo.", ephemeral=True)
            return

        # Finalizar tuneo en curso si existe
        if uid in tuneos_activos:
            dinero_tuneo = tuneos_activos.pop(uid)["dinero"]
            turnos_activos[uid]["dinero"] += dinero_tuneo
            if uid not in historial_tuneos:
                historial_tuneos[uid] = {"dinero_total": 0, "tuneos": 0}
            historial_tuneos[uid]["dinero_total"] += dinero_tuneo
            historial_tuneos[uid]["tuneos"] += 1

        total_dinero = turnos_activos.pop(uid)["dinero"]
        if uid not in historial_tuneos:
            historial_tuneos[uid] = {"dinero_total": 0, "tuneos": 0}
        historial_tuneos[uid]["dinero_total"] += total_dinero

        await interaction.followup.send(f"✅ Turno finalizado. Total dinero acumulado: ${total_dinero:,}", ephemeral=True)

    button_finalizar_turno.callback = finalizar_turno_callback
    view_turno.add_item(button_finalizar_turno)

    await canal_turnos.send("Pulsa los botones para gestionar tu turno:", view=view_turno)

    # --------------------------
    # Mensaje Tuneos - Botones de tuneo + finalizar tuneo
    # --------------------------
    view_tuneos = View()
    for tuneo, precio in precios_tuneos.items():
        button = Button(label=f"{tuneo} (${precio:,})", style=discord.ButtonStyle.blurple)

        async def tuneo_callback(interaction: discord.Interaction, t=tuneo, p=precio):
            uid = interaction.user.id
            await interaction.response.defer(ephemeral=True)
            if uid not in turnos_activos:
                await interaction.followup.send("❌ No tienes un turno activo.", ephemeral=True)
                return
            if uid not in tuneos_activos:
                tuneos_activos[uid] = {"dinero": 0}
            tuneos_activos[uid]["dinero"] += p
            total = tuneos_activos[uid]["dinero"]
            await interaction.followup.send(f"🔧 Añadido {t}. Total tuneo: ${total:,}", ephemeral=True)

        button.callback = tuneo_callback
        view_tuneos.add_item(button)

    # Botón finalizar tuneo
    button_finalizar_tuneo = Button(label="✅ Finalizar Tuneo", style=discord.ButtonStyle.green)

    async def finalizar_tuneo_callback(interaction: discord.Interaction):
        uid = interaction.user.id
        await interaction.response.defer(ephemeral=True)
        if uid not in tuneos_activos:
            await interaction.followup.send("❌ No tienes tuneos activos.", ephemeral=True)
            return

        dinero_tuneo = tuneos_activos.pop(uid)["dinero"]
        turnos_activos[uid]["dinero"] += dinero_tuneo

        if uid not in historial_tuneos:
            historial_tuneos[uid] = {"dinero_total": 0, "tuneos": 0}
        historial_tuneos[uid]["dinero_total"] += dinero_tuneo
        historial_tuneos[uid]["tuneos"] += 1

        await interaction.followup.send(f"✅ Tuneo finalizado. Dinero: ${dinero_tuneo:,} registrado como 1 tuneo.", ephemeral=True)

    button_finalizar_tuneo.callback = finalizar_tuneo_callback
    view_tuneos.add_item(button_finalizar_tuneo)

    await canal_tuneos.send("Pulsa los botones para registrar tus tuneos y finalizar cada tuneo:", view=view_tuneos)

    # --------------------------
    # Mensaje Staff - Historial total
    # --------------------------
    view_historial = View()
    button_historial = Button(label="📋 Historial Total", style=discord.ButtonStyle.gray)

    async def historial_callback(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not any(role.id in ROLES_HISTORIAL_TOTAL for role in interaction.user.roles):
            await interaction.followup.send("❌ No tienes permiso para ver el historial completo.", ephemeral=True)
            return
        if not historial_tuneos:
            await interaction.followup.send("❌ No hay tuneos registrados.", ephemeral=True)
            return
        msg = "📋 Historial completo de tuneos:\n"
        for uid, datos in historial_tuneos.items():
            user = interaction.guild.get_member(uid)
            nombre = user.display_name if user else f"ID:{uid}"
            total_tuneos = datos.get("tuneos", 0)
            msg += f"- {nombre}: {total_tuneos} tuneos\n"
        await interaction.followup.send(msg, ephemeral=True)

    button_historial.callback = historial_callback
    view_historial.add_item(button_historial)
    await canal_staff.send("Pulsa el botón para ver el historial completo de tuneos:", view=view_historial)

bot.run(os.getenv("DISCORD_TOKEN"))
