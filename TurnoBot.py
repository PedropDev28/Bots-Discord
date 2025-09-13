import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from datetime import datetime, timedelta
import pytz
import os
import re
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
# Precios de los tuneos
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

# ------------------------------
# Roles por ID
# ------------------------------
ROLES_TUNEO = [1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425, 1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423, 1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882, 1391019755267424347, 1385301435456950391, 1385301435456950390, 1415954460202766386]
ROLES_HISTORIAL_TOTAL = [1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425, 1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423, 1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882, 1415954460202766386]

# ------------------------------
# Datos del bot
# ------------------------------
turnos_activos = {}      # user_id -> {"dinero": int, "inicio": datetime}
tuneos_activos = {}      # user_id -> {"dinero": int}
historial_tuneos = {}    # user_id -> {"dinero_total": int, "tuneos": int, "detalle": list}

# Canal de identificación de mecánicos
CANAL_IDENTIFICACION = 1398583186610716682
ROLE_APRENDIZ = 1385301435456950390
ROLE_OVERSPEED = 1387571297705394250

# Canal staff y ranking
CANAL_STAFF = 1415964136550043689
CANAL_RANKING = 1416021337519947858

# Canal keep-alive
CANAL_KEEPALIVE = 1387055864866799637

# ------------------------------
# Estados rotativos
# ------------------------------
estados = itertools.cycle([
    # Profesionales
    discord.Game("Gestionando turnos ⏱️"),
    discord.Activity(type=discord.ActivityType.listening, name="a los reportes del staff 📋"),
    discord.Activity(type=discord.ActivityType.watching, name="los tuneos en curso 🔧"),
    discord.Activity(type=discord.ActivityType.competing, name="por ser el mejor mecánico 💰"),
    # Divertidos / Roleplay
    discord.Game("tunear hasta el fin 🚗💨"),
    discord.Activity(type=discord.ActivityType.listening, name="los escapes sonar 🔊"),
    discord.Activity(type=discord.ActivityType.watching, name="el humo del taller 🚬"),
    discord.Activity(type=discord.ActivityType.competing, name="con Fast & Furious 🏎️🔥"),
    discord.Game("con aceite y gasolina ⛽"),
    discord.Activity(type=discord.ActivityType.watching, name="a los clientes esperar 😅")
])

@tasks.loop(minutes=10)
async def rotar_estado():
    estado = next(estados)
    await bot.change_presence(activity=estado)

# ------------------------------
# Función de inicialización de mensajes fijos
# ------------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    keep_alive.start()
    rotar_estado.start()  # iniciar rotación de estados

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

        await interaction.followup.send(
            f"✅ Turno finalizado. Total dinero acumulado: ${total_dinero:,}\n⏱️ Duración: {duracion}",
            ephemeral=True
        )

        await canal_staff.send(
            f"📋 **{interaction.user.display_name}** finalizó su turno.\n"
            f"⏱️ Duración: {duracion}\n"
            f"💰 Dinero total: ${total_dinero:,}\n"
            f"🔧 Tuneos acumulados: {historial_tuneos[uid]['tuneos']}"
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

    # --------------------------
    # Mensaje Staff - Historial total con botón
    # --------------------------
    view_historial = View(timeout=None)
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

    # --------------------------
    # Ranking automático
    # --------------------------
    ranking_task.start()

# ------------------------------
# Ranking semanal y mensual
# ------------------------------
@tasks.loop(hours=24)
async def ranking_task():
    ahora = datetime.now(zona)
    canal = bot.get_channel(CANAL_RANKING)

    # Ranking semanal
    if ahora.weekday() == 6:  # Domingo
        ranking = sorted(historial_tuneos.items(), key=lambda x: x[1]["tuneos"], reverse=True)[:5]
        if ranking:
            msg = "🏆 **Ranking semanal de mecánicos:**\n"
            for i, (uid, datos) in enumerate(ranking, 1):
                user = canal.guild.get_member(uid)
                nombre = user.display_name if user else f"ID:{uid}"
                msg += f"{i}️⃣ {nombre} - {datos['tuneos']} tuneos\n"
            await canal.send(msg)

    # Ranking mensual (último día del mes)
    mañana = ahora + timedelta(days=1)
    if mañana.month != ahora.month:
        ranking = sorted(historial_tuneos.items(), key=lambda x: x[1]["tuneos"], reverse=True)[:5]
        if ranking:
            msg = "🏆 **Ranking mensual de mecánicos:**\n"
            for i, (uid, datos) in enumerate(ranking, 1):
                user = canal.guild.get_member(uid)
                nombre = user.display_name if user else f"ID:{uid}"
                msg += f"{i}️⃣ {nombre} - {datos['tuneos']} tuneos\n"
            await canal.send(msg)

# ------------------------------
# Comando staff: historial detallado
# ------------------------------
@bot.command()
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def historial(ctx, member: discord.Member):
    uid = member.id
    if uid not in historial_tuneos:
        return await ctx.send(f"❌ {member.display_name} no tiene tuneos registrados.")
    datos = historial_tuneos[uid]
    msg = f"📋 Historial de {member.display_name}:\n"
    for fecha, dinero, detalle in datos["detalle"]:
        msg += f"- {fecha.strftime('%d/%m/%Y %H:%M')} → ${dinero:,} ({detalle})\n"
    msg += f"\n🔧 Total: {datos['tuneos']} tuneos | 💰 ${datos['dinero_total']:,}"
    await ctx.send(msg)

# ------------------------------
# Comando staff: limpiar mensajes
# ------------------------------
@bot.command()
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def borrar(ctx, cantidad: int):
    await ctx.channel.purge(limit=cantidad + 1)
    await ctx.send(f"🧹 Se borraron {cantidad} mensajes.", delete_after=5)

# ------------------------------
# Identificación de mecánicos
# ------------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == CANAL_IDENTIFICACION:
        match = re.match(r"ID IC:\s*(\d+)\s+NOMBRE IC:\s*(.+)", message.content, re.IGNORECASE)
        if match:
            user_id_ic = match.group(1)
            nombre_ic = match.group(2)
            try:
                nuevo_apodo = f"🧰 APR | {nombre_ic} | {user_id_ic}"
                await message.author.edit(nick=nuevo_apodo)

                rol1 = message.guild.get_role(ROLE_APRENDIZ)
                rol2 = message.guild.get_role(ROLE_OVERSPEED)
                if rol1: await message.author.add_roles(rol1)
                if rol2: await message.author.add_roles(rol2)

                await message.add_reaction("✅")

            except discord.Forbidden:
                await message.add_reaction("⚠️")
        else:
            await message.add_reaction("❌")
            try:
                await message.author.send(
                    "⚠️ Tu identificación no sigue el formato correcto.\n\n"
                    "Usa este formato:\n"
                    "`ID IC: 99999 NOMBRE IC: John Doe`\n\n"
                    "🔧 Una vez lo corrijas, el bot actualizará tu apodo automáticamente."
                )
            except discord.Forbidden:
                await message.channel.send(
                    f"{message.author.mention} ⚠️ No pude enviarte un mensaje privado."
                )

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
# Ejecutar bot
# ------------------------------
bot.run(os.getenv("DISCORD_TOKEN"))
