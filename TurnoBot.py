import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from datetime import datetime, timedelta
import pytz
import os
import re

# ------------------------------
# Configuración inicial
# ------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
zona = pytz.timezone("Europe/Madrid")

# ------------------------------
# Datos del bot
# ------------------------------
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

turnos_activos = {}
tuneos_activos = {}
historial_tuneos = {}

# ------------------------------
# IDs (ajusta los tuyos)
# ------------------------------
CANAL_TURNOS = 1415949790545711236
CANAL_TUNEOS = 1415963375485321226
CANAL_STAFF = 1415964136550043689
CANAL_RANKING = 1416021337519947858
CANAL_IDENTIFICACION = 1398583186610716682
ROLE_APRENDIZ = 1385301435456950390
ROLE_OVERSPEED = 1387571297705394250

ROLES_TUNEO = [1385301435499151429]
ROLES_HISTORIAL_TOTAL = [1385301435499151429]

# ------------------------------
# Views Persistentes
# ------------------------------

class TurnoView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⏱️ Iniciar Turno", style=discord.ButtonStyle.green, custom_id="iniciar_turno")
    async def iniciar_turno(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if not any(role.id in ROLES_TUNEO for role in interaction.user.roles):
            return await interaction.response.send_message("❌ No tienes permiso para iniciar un turno.", ephemeral=True)
        if uid in turnos_activos:
            return await interaction.response.send_message("❌ Ya tienes un turno activo.", ephemeral=True)

        turnos_activos[uid] = {"dinero": 0, "inicio": datetime.now(zona)}
        await interaction.response.send_message("✅ Tu turno ha comenzado.", ephemeral=True)

    @discord.ui.button(label="✅ Finalizar Turno", style=discord.ButtonStyle.red, custom_id="finalizar_turno")
    async def finalizar_turno(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid not in turnos_activos:
            return await interaction.response.send_message("❌ No tienes un turno activo.", ephemeral=True)

        if uid in tuneos_activos:
            dinero_tuneo = tuneos_activos.pop(uid)["dinero"]
            turnos_activos[uid]["dinero"] += dinero_tuneo
            historial_tuneos.setdefault(uid, {"dinero_total": 0, "tuneos": 0, "detalle": []})
            historial_tuneos[uid]["dinero_total"] += dinero_tuneo
            historial_tuneos[uid]["tuneos"] += 1
            historial_tuneos[uid]["detalle"].append((datetime.now(zona), dinero_tuneo, "Finalizado auto al cerrar turno"))

        datos_turno = turnos_activos.pop(uid)
        total_dinero = datos_turno["dinero"]
        inicio = datos_turno["inicio"]
        duracion = datetime.now(zona) - inicio

        historial_tuneos.setdefault(uid, {"dinero_total": 0, "tuneos": 0, "detalle": []})
        historial_tuneos[uid]["dinero_total"] += total_dinero

        await interaction.response.send_message(
            f"✅ Turno finalizado. Total dinero acumulado: ${total_dinero:,}\n⏱️ Duración: {duracion}",
            ephemeral=True
        )

        canal_staff = bot.get_channel(CANAL_STAFF)
        await canal_staff.send(
            f"📋 **{interaction.user.display_name}** finalizó su turno.\n"
            f"⏱️ Duración: {duracion}\n"
            f"💰 Dinero total: ${total_dinero:,}\n"
            f"🔧 Tuneos acumulados: {historial_tuneos[uid]['tuneos']}"
        )


class TuneosView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for tuneo, precio in precios_tuneos.items():
            self.add_item(Button(label=f"{tuneo} (${precio:,})", style=discord.ButtonStyle.blurple, custom_id=f"tuneo_{tuneo}"))

    @discord.ui.button(label="✅ Finalizar Tuneo", style=discord.ButtonStyle.green, custom_id="finalizar_tuneo")
    async def finalizar_tuneo(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid not in tuneos_activos:
            return await interaction.response.send_message("❌ No tienes tuneos activos.", ephemeral=True)

        dinero_tuneo = tuneos_activos.pop(uid)["dinero"]
        turnos_activos[uid]["dinero"] += dinero_tuneo

        historial_tuneos.setdefault(uid, {"dinero_total": 0, "tuneos": 0, "detalle": []})
        historial_tuneos[uid]["dinero_total"] += dinero_tuneo
        historial_tuneos[uid]["tuneos"] += 1
        historial_tuneos[uid]["detalle"].append((datetime.now(zona), dinero_tuneo, "Tuneo completado"))

        await interaction.response.send_message(
            f"✅ Tuneo finalizado. Dinero: ${dinero_tuneo:,} registrado como 1 tuneo.",
            ephemeral=True
        )


class HistorialView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Historial Total", style=discord.ButtonStyle.gray, custom_id="historial_total")
    async def historial_total(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in ROLES_HISTORIAL_TOTAL for role in interaction.user.roles):
            return await interaction.response.send_message("❌ No tienes permiso.", ephemeral=True)
        if not historial_tuneos:
            return await interaction.response.send_message("❌ No hay tuneos registrados.", ephemeral=True)

        msg = "📋 Historial completo:\n"
        for uid, datos in historial_tuneos.items():
            user = interaction.guild.get_member(uid)
            nombre = user.display_name if user else f"ID:{uid}"
            msg += f"- {nombre}: {datos['tuneos']} tuneos\n"
        await interaction.response.send_message(msg, ephemeral=True)


# ------------------------------
# Eventos
# ------------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    # Re-registrar Views persistentes
    bot.add_view(TurnoView())
    bot.add_view(TuneosView())
    bot.add_view(HistorialView())

    # (Opcional) enviar mensajes fijos una sola vez al crear el bot
    # canal_turnos = bot.get_channel(CANAL_TURNOS)
    # await canal_turnos.send("Pulsa los botones para gestionar tu turno:", view=TurnoView())


# ------------------------------
# Arrancar el bot
# ------------------------------
bot.run(os.getenv("DISCORD_TOKEN"))
