import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
from datetime import datetime, timedelta
import pytz
import os
import itertools

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
# Roles por ID
# ------------------------------
ROLES_TUNEO = [1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425,
               1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423,
               1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882,
               1391019755267424347, 1385301435456950391, 1385301435456950390, 1415954460202766386]

ROLES_HISTORIAL_TOTAL = [1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425,
                         1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423,
                         1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882,
                         1415954460202766386]

ROLE_APRENDIZ = 1385301435456950390
ROLE_OVERSPEED = 1387571297705394250

# Canal identificación mecánicos
CANAL_IDENTIFICACION = 1398583186610716682
CANAL_STAFF = 1415964136550043689
CANAL_RANKING = 1416021337519947858
CANAL_KEEPALIVE = 1387055864866799637

# ------------------------------
# Precios de los tuneos
# ------------------------------
precios_tuneos = {
    "Frenos": 80000, "Motor": 80000, "Suspensión": 80000, "Transmisión": 80000,
    "Blindaje": 105000, "Turbo": 100000, "Full tuning con blindaje": 525000,
    "Full tuning sin blindaje": 450000, "Cambio estético": 20000,
    "Reparación en el taller": 10000, "Reparación en la calle": 15000, "Kit de reparación": 50000
}

# ------------------------------
# Datos del bot
# ------------------------------
turnos_activos = {}      # user_id -> {"dinero": int, "inicio": datetime}
tuneos_activos = {}      # user_id -> {"dinero": int}
historial_tuneos = {}    # user_id -> {"dinero_total": int, "tuneos": int, "detalle": list}

# ------------------------------
# Estados rotativos
# ------------------------------
estados = itertools.cycle([
    "Gestionando turnos ⏱️",
    "Escuchando reportes 📋",
    "Vigilando tuneos 🔧",
    "Compitiendo por ser el mejor 💰",
    "Tunear hasta el fin 🚗💨",
    "Escuchando escapes sonar 🔊",
    "Observando humo del taller 🚬",
    "Compitiendo con Fast & Furious 🏎️🔥",
    "Con aceite y gasolina ⛽",
    "Observando clientes esperar 😅"
])

@tasks.loop(minutes=5)
async def rotar_estado():
    mec_activos = len(turnos_activos)
    estado_texto = next(estados)
    actividad = discord.Game(f"{estado_texto} | Mecánicos activos: {mec_activos}")
    await bot.change_presence(activity=actividad)

# ------------------------------
# Modal de identificación
# ------------------------------
class IdentificacionModal(Modal, title="Identificación de mecánico"):
    nombre_ic = TextInput(label="Nombre IC", placeholder="Ej: John Doe", max_length=32)
    id_ic = TextInput(label="ID IC", placeholder="Ej: 12345", max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        nuevo_apodo = f"🧰 APR | {self.nombre_ic.value} | {self.id_ic.value}"
        try:
            await interaction.user.edit(nick=nuevo_apodo)
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ No tengo permisos para cambiar tu apodo.", ephemeral=True)
            return

        rol1 = interaction.guild.get_role(ROLE_APRENDIZ)
        rol2 = interaction.guild.get_role(ROLE_OVERSPEED)
        if rol1: await interaction.user.add_roles(rol1)
        if rol2: await interaction.user.add_roles(rol2)

        await interaction.response.send_message(f"✅ Identificación completada. Apodo cambiado a: {nuevo_apodo}", ephemeral=True)

# ------------------------------
# Evento de mensaje en canal de identificación
# ------------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == CANAL_IDENTIFICACION:
        await message.delete()
        await message.author.send("Por favor completa el formulario para identificarte en el servidor.")
        await message.author.send_modal(IdentificacionModal())

    await bot.process_commands(message)

# --------------------------
# Mantener el bot activo en Railway
# --------------------------
@tasks.loop(minutes=10)
async def keep_alive():
    canal = bot.get_channel(CANAL_KEEPALIVE)
    if canal:
        try:
            await canal.send("💤 Ping para mantener activo el bot.", delete_after=2)
        except Exception as e:
            print(f"No se pudo enviar el ping de keep_alive: {e}")

# ------------------------------
# on_ready con botones y ranking
# ------------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    keep_alive.start()
    rotar_estado.start()

    canal_turnos = bot.get_channel(1415949790545711236)
    canal_tuneos = bot.get_channel(1415963375485321226)
    canal_staff = bot.get_channel(CANAL_STAFF)

    # --------------------------
    # Mensaje Turnos
    # --------------------------
    view_turno = View(timeout=None)
    button_turno = Button(label="⏱️ Iniciar Turno", style=discord.ButtonStyle.green)

    async def iniciar_callback(interaction: discord.Interaction):
        uid = interaction.user.id
        await interaction.response.defer(ephemeral=True)
        if not any(role.id in ROLES_TUNEO for role in interaction.user.roles):
            return await interaction.followup.send("❌ No tienes permiso para iniciar un turno.", ephemeral=True)
        if uid in turnos_activos:
            return await interaction.followup.send("❌ Ya tienes un turno activo.", ephemeral=True)
        turnos_activos[uid] = {"dinero": 0, "inicio": datetime.now(zona)}
        await interaction.followup.send("✅ Tu turno ha comenzado.", ephemeral=True)

    button_turno.callback = iniciar_callback
    view_turno.add_item(button_turno)

    button_finalizar_turno = Button(label="✅ Finalizar Turno", style=discord.ButtonStyle.red)

    async def finalizar_turno_callback(interaction: discord.Interaction):
        uid = interaction.user.id
        await interaction.response.defer(ephemeral=True)
        if uid not in turnos_activos:
            return await interaction.followup.send("❌ No tienes un turno activo.", ephemeral=True)

        # Añadir tuneos activos al total
        if uid in tuneos_activos:
            dinero_tuneo = tuneos_activos.pop(uid)["dinero"]
            turnos_activos[uid]["dinero"] += dinero_tuneo
            if uid not in historial_tuneos:
                historial_tuneos[uid] = {"dinero_total": 0, "tuneos": 0, "detalle": []}
            historial_tuneos[uid]["dinero_total"] += dinero_tuneo
            historial_tuneos[uid]["tuneos"] += 1
            historial_tuneos[uid]["detalle"].append(
                (datetime.now(zona), dinero_tuneo, "Finalizado auto al cerrar turno")
            )

        datos_turno = turnos_activos.pop(uid)
        total_dinero = datos_turno["dinero"]
        inicio = datos_turno["inicio"]
        duracion = datetime.now(zona) - inicio

        if uid not in historial_tuneos:
            historial_tuneos[uid] = {"dinero_total": 0, "tuneos": 0, "detalle": []}
        historial_tuneos[uid]["dinero_total"] += total_dinero

        # Mensaje al mecánico solo
        await interaction.followup.send(
            f"✅ Turno finalizado. Total dinero acumulado: ${total_dinero:,}\n⏱️ Duración: {duracion}",
            ephemeral=True
        )

    button_finalizar_turno.callback = finalizar_turno_callback
    view_turno.add_item(button_finalizar_turno)
    await canal_turnos.send("Pulsa los botones para gestionar tu turno:", view=view_turno)

    # --------------------------
    # Mensaje Tuneos
    # --------------------------
    view_tuneos = View(timeout=None)
    for tuneo, precio in precios_tuneos.items():
        button = Button(label=f"{tuneo} (${precio:,})", style=discord.ButtonStyle.blurple)

        async def tuneo_callback(interaction: discord.Interaction, t=tuneo, p=precio):
            uid = interaction.user.id
            await interaction.response.defer(ephemeral=True)
            if uid not in turnos_activos:
                return await interaction.followup.send("❌ No tienes un turno activo.", ephemeral=True)
            if uid not in tuneos_activos:
                tuneos_activos[uid] = {"dinero": 0}
            tuneos_activos[uid]["dinero"] += p
            total = tuneos_activos[uid]["dinero"]
            await interaction.followup.send(f"🔧 Añadido {t}. Total tuneo: ${total:,}", ephemeral=True)

        button.callback = tuneo_callback
        view_tuneos.add_item(button)

    button_finalizar_tuneo = Button(label="✅ Finalizar Tuneo", style=discord.ButtonStyle.green)

    async def finalizar_tuneo_callback(interaction: discord.Interaction):
        uid = interaction.user.id
        await interaction.response.defer(ephemeral=True)
        if uid not in tuneos_activos:
            return await interaction.followup.send("❌ No tienes tuneos activos.", ephemeral=True)

        dinero_tuneo = tuneos_activos.pop(uid)["dinero"]
        turnos_activos[uid]["dinero"] += dinero_tuneo

        if uid not in historial_tuneos:
            historial_tuneos[uid] = {"dinero_total": 0, "tuneos": 0, "detalle": []}
        historial_tuneos[uid]["dinero_total"] += dinero_tuneo
        historial_tuneos[uid]["tuneos"] += 1
        historial_tuneos[uid]["detalle"].append(
            (datetime.now(zona), dinero_tuneo, "Tuneo completado")
        )

        # Premios especiales
        if historial_tuneos[uid]["tuneos"] in [50, 100, 200]:
            await canal_staff.send(
                f"🎉 ¡Felicidades {interaction.user.mention}! Has alcanzado {historial_tuneos[uid]['tuneos']} tuneos, premio disponible 🎁."
            )

        await interaction.followup.send(
            f"✅ Tuneo finalizado. Dinero: ${dinero_tuneo:,} registrado como 1 tuneo.",
            ephemeral=True
        )

    button_finalizar_tuneo.callback = finalizar_tuneo_callback
    view_tuneos.add_item(button_finalizar_tuneo)
    await canal_tuneos.send("Pulsa los botones para registrar tus tuneos y finalizar cada tuneo:", view=view_tuneos)

# ------------------------------
# Ejecutar bot
# ------------------------------
bot.run(os.getenv("DISCORD_TOKEN"))
