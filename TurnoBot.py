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
# Roles por ID (configura según tu servidor)
# ------------------------------
ROLES_TUNEO = [
    1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425,
    1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423,
    1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882,
    1391019755267424347, 1385301435456950391, 1385301435456950390, 1415954460202766386
]

# Si quieres restringir comandos (historial/borrar) a ciertos roles, mantenlos aquí
ROLES_HISTORIAL_TOTAL = [
    1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425,
    1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423,
    1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882,
    1415954460202766386
]

ROL_PROPIETARIO = 1410548111788740620  # Solo este rol puede usar !cambiarrol
ROL_MIEMBRO = 1387524774485299391      # Para avisos DM

# Diccionario de roles especiales y sus prefijos de apodo
ROLES_APODOS = {
    1385301435456950391: ("🔧 MEC", "MEC"),          # Mecánico
    1391019848414400583: ("⭐ GER", "GER"),           # Gerente
    1385301435499151423: ("⭐ JEF", "JEF"),          # Jefe mecánico
    1391019868630945882: ("⭐ SUBGER", "SUBGER"),     # Subgerente
    1385301435499151422: ("⭐ SUBJEF", "SUBJEF"),     # Subjefe
    1385301435456950394: ("👑 GER. GEN.", "GER. GEN."), # Gerente general
    1391019755267424347: ("📋 REC", "REC"),          # Reclutador
    1385301435456950390: ("🧰 APR", "APR"),          # Aprendiz
}

# ------------------------------
# Canales (CAMBIAR_AQUI por tus IDs reales)
# ------------------------------
CANAL_IDENTIFICACION = 1398583186610716682  # canal con botón de identificación
ROLE_APRENDIZ = 1385301435456950390
ROLE_OVERSPEED = 1387571297705394250
CANAL_TURNOS = 1415949790545711236
CANAL_TUNEOS = 1415963375485321226
CANAL_RANKING = 1416021337519947858
CANAL_KEEPALIVE = 1387055864866799637
CANAL_ANUNCIOS = 1387551821224214839

# ------------------------------
# Datos runtime
# ------------------------------
turnos_activos = {}      # user_id -> {"dinero": int, "inicio": datetime}
tuneos_activos = {}      # user_id -> {"dinero": int}
historial_tuneos = {}    # user_id -> {"dinero_total": int, "tuneos": int, "detalle": list}
avisados_identificacion = set()

# ------------------------------
# Estados rotativos
# ------------------------------
estados = itertools.cycle([
    discord.Game("Gestionando turnos ⏱️"),
    discord.Activity(type=discord.ActivityType.listening, name="a los reportes 📋"),
    discord.Activity(type=discord.ActivityType.watching, name="los tuneos en curso 🔧"),
    discord.Activity(type=discord.ActivityType.competing, name="por ser el mejor mecánico 💰"),
    discord.Game("tunear hasta el fin 🚗💨"),
    discord.Activity(type=discord.ActivityType.listening, name="los escapes sonar 🔊"),
    discord.Activity(type=discord.ActivityType.watching, name="el humo del taller 🚬"),
    discord.Activity(type=discord.ActivityType.competing, name="con Fast & Furious 🏎️🔥"),
    discord.Game("con aceite y gasolina ⛽"),
    discord.Activity(type=discord.ActivityType.watching, name="a los clientes esperar 😅")
])

@tasks.loop(minutes=10)
async def rotar_estado():
    mec_activos = 0
    for guild in bot.guilds:
        for miembro in guild.members:
            try:
                if any(role.id in ROLES_TUNEO for role in miembro.roles):
                    mec_activos += 1
            except Exception:
                continue
    estado = next(estados)
    # El objeto puede ser Game o Activity; mostramos su nombre si existe
    nombre_estado = getattr(estado, "name", None) or getattr(estado, "type", "Mecánicos")
    try:
        await bot.change_presence(activity=discord.Game(f"{nombre_estado} | Mecánicos activos: {mec_activos}"))
    except Exception:
        # fallback sencillo
        await bot.change_presence(activity=discord.Game(f"Mecánicos activos: {mec_activos}"))

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
        if rol1:
            try:
                await interaction.user.add_roles(rol1)
            except Exception:
                pass
        if rol2:
            try:
                await interaction.user.add_roles(rol2)
            except Exception:
                pass

        # Crear o buscar thread privado en CANAL_IDENTIFICACION para registrar la identificación
        canal = interaction.guild.get_channel(CANAL_IDENTIFICACION)
        thread_name = "Identificaciones Mecánicos"
        thread = None
        if canal:
            async for th in canal.threads:
                if th.name == thread_name:
                    thread = th
                    break
            if thread is None:
                try:
                    thread = await canal.create_thread(
                        name=thread_name,
                        type=discord.ChannelType.private_thread,
                        invitable=False
                    )
                    await thread.edit(invitable=False)
                except Exception:
                    thread = None
            if thread:
                try:
                    # Añadimos un mensaje al thread con la identificación (no mencionamos staff)
                    msg = await thread.send(f"{interaction.user.mention} identificado como: **{nuevo_apodo}**")
                    await msg.add_reaction("✅")
                except Exception:
                    pass

        await interaction.response.send_message(
            f"✅ Identificación completada. Apodo cambiado a: {nuevo_apodo}",
            ephemeral=True
        )

# ------------------------------
# Borrar mensajes en canal de identificación si alguien escribe (solo botón -> no comandos)
# ------------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    try:
        if message.channel.id == CANAL_IDENTIFICACION:
            await message.delete()
            return
    except Exception:
        pass
    await bot.process_commands(message)

# ------------------------------
# Aviso por DM para los miembros que no se han identificado
# ------------------------------
@tasks.loop(hours=1)
async def avisar_miembros_identificacion():
    for guild in bot.guilds:
        rol_miembro = guild.get_role(ROL_MIEMBRO)
        if rol_miembro is None:
            continue
        for miembro in rol_miembro.members:
            # Saltar si ya tiene rol de mecánico
            if any(role.id in ROLES_TUNEO for role in miembro.roles):
                continue
            if miembro.id in avisados_identificacion:
                continue
            try:
                await miembro.send(
                    f"¡Hola {miembro.display_name}! Para poder ejercer como mecánico, por favor identifícate en el canal <#{CANAL_IDENTIFICACION}> pulsando el botón y rellenando el formulario. "
                    "Si ya lo hiciste, puedes ignorar este mensaje."
                )
                avisados_identificacion.add(miembro.id)
            except Exception:
                # usuarios con DMs cerrados o errores se ignoran
                pass

# ------------------------------
# Tareas recurrentes
# ------------------------------
@tasks.loop(minutes=10)
async def keep_alive():
    canal = bot.get_channel(CANAL_KEEPALIVE)
    if canal:
        try:
            await canal.send("💤 Ping para mantener activo el bot.", delete_after=2)
        except Exception:
            pass

@tasks.loop(hours=24)
async def ranking_task():
    ahora = datetime.now(zona)
    canal = bot.get_channel(CANAL_RANKING)
    if canal is None:
        return
    # Ranking semanal (domingo)
    try:
        if ahora.weekday() == 6:  # Domingo
            ranking = sorted(historial_tuneos.items(), key=lambda x: x[1]["tuneos"], reverse=True)[:5]
            if ranking:
                msg = "🏆 **Ranking semanal de mecánicos:**\n"
                for i, (uid, datos) in enumerate(ranking, 1):
                    user = canal.guild.get_member(uid)
                    nombre = user.display_name if user else f"ID:{uid}"
                    msg += f"{i}️⃣ {nombre} - {datos['tuneos']} tuneos\n"
                await canal.send(msg)
        # Ranking mensual: comprobar si mañana es mes distinto
        manana = ahora + timedelta(days=1)
        if manana.month != ahora.month:
            ranking = sorted(historial_tuneos.items(), key=lambda x: x[1]["tuneos"], reverse=True)[:5]
            if ranking:
                msg = "🏆 **Ranking mensual de mecánicos:**\n"
                for i, (uid, datos) in enumerate(ranking, 1):
                    user = canal.guild.get_member(uid)
                    nombre = user.display_name if user else f"ID:{uid}"
                    msg += f"{i}️⃣ {nombre} - {datos['tuneos']} tuneos\n"
                await canal.send(msg)
    except Exception:
        pass

# ------------------------------
# Función para enviar anuncio embed (sin mencionar staff)
# ------------------------------
async def enviar_anuncio():
    canal = bot.get_channel(CANAL_ANUNCIOS)
    if canal is None:
        return
    embed = discord.Embed(
        title="📢 ANUNCIO IMPORTANTE – MECÁNICOS OVERSPEED 🔧🚗💨",
        description="Nuestro bot ya está operativo para gestionar **turnos y tuneos**.\n\n"
                    "✅ **Todo se maneja con botones, no con comandos.**",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="📝 Identificación",
        value=f"En <#{CANAL_IDENTIFICACION}> pulsa el botón para identificarte como **Mecánico**.\n"
              "Se te asignará el rol de **Aprendiz** y tu apodo se ajustará automáticamente.",
        inline=False
    )

    embed.add_field(
        name="⏱️ Turnos",
        value=f"En <#{CANAL_TURNOS}> tienes los botones:\n"
              "`⏱️ Iniciar Turno` → Empiezas tu turno.\n"
              "`✅ Finalizar Turno` → Terminas y ves el total acumulado.",
        inline=False
    )

    embed.add_field(
        name="🔧 Tuneos",
        value=f"En <#{CANAL_TUNEOS}> están los botones de cada tuneo con su precio.\n"
              "Pulsa los que realices y al terminar usa `✅ Finalizar Tuneo`.\n"
              "Cada tuneo cuenta para los **rankings y premios** 🏆",
        inline=False
    )

    embed.add_field(
        name="🏆 Rankings",
        value=f"Cada semana y mes se publica en <#{CANAL_RANKING}> el **TOP 5 de mecánicos**.",
        inline=False
    )

    embed.add_field(
        name="⚠️ Comando especial",
        value="El comando `!cambiarrol @usuario <id_rol>` es **exclusivo del Propietario** (rol propietario). "
              "Los demás deben usar siempre los botones.",
        inline=False
    )

    embed.set_footer(text="🔧 Overspeed RP | Taller Oficial")
    try:
        await canal.send(embed=embed)
    except Exception:
        pass

# ------------------------------
# Comandos: historial y borrar (verificados por roles)
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
        try:
            msg += f"- {fecha.strftime('%d/%m/%Y %H:%M')} → ${dinero:,} ({detalle})\n"
        except Exception:
            # en caso de datos mal formateados
            msg += f"- {fecha} → ${dinero:,} ({detalle})\n"
    msg += f"\n🔧 Total: {datos['tuneos']} tuneos | 💰 ${datos['dinero_total']:,}"
    await ctx.send(msg)

@bot.command()
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def borrar(ctx, cantidad: int):
    deleted = await ctx.channel.purge(limit=cantidad + 1)
    await ctx.send(f"🧹 Se borraron {len(deleted)-1 if len(deleted)>0 else 0} mensajes.", delete_after=5)

# ------------------------------
# Comando cambiarrol - SOLO PROPIETARIO
# ------------------------------
@bot.command()
async def cambiarrol(ctx, miembro: discord.Member, id_rol: int):
    """Cambia el rol y apodo de un usuario (solo propietario)."""
    # Verificación estricta: solo si el autor tiene el rol propietario
    if ROL_PROPIETARIO not in [r.id for r in ctx.author.roles]:
        await ctx.send("❌ Solo el Propietario puede usar este comando.")
        return

    rol_obj = ctx.guild.get_role(id_rol)
    if not rol_obj:
        await ctx.send("❌ Ese rol no existe en este servidor.")
        return

    prefijo = ROLES_APODOS.get(id_rol)
    if not prefijo:
        await ctx.send("❌ Ese rol no tiene prefijo configurado.")
        return

    # Quitar otros roles de apodo si los tuviera
    roles_a_quitar = [ctx.guild.get_role(rid) for rid in ROLES_APODOS.keys() if rid != id_rol]
    try:
        await miembro.remove_roles(*[r for r in roles_a_quitar if r in miembro.roles])
    except Exception:
        pass

    if rol_obj not in miembro.roles:
        try:
            await miembro.add_roles(rol_obj)
        except Exception:
            pass

    apodo = miembro.display_name
    partes = apodo.split('|')
    if len(partes) == 3:
        nombre = partes[1].strip()
        idic = partes[2].strip()
        nuevo_apodo = f"{prefijo[0]} | {nombre} | {idic}"
        try:
            await miembro.edit(nick=nuevo_apodo)
            await ctx.send(f"✅ {miembro.mention} ahora es `{nuevo_apodo}` y tiene el rol {rol_obj.mention}")
        except discord.Forbidden:
            await ctx.send("⚠️ No tengo permisos para cambiar el apodo de ese usuario.")
    else:
        await ctx.send("⚠️ El apodo de este usuario no tiene el formato esperado. Formato esperado: `[emoji] ROL | Nombre | ID`")

# ------------------------------
# on_ready -> iniciar tareas y crear vistas con botones
# ------------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    # Iniciar tareas
    try:
        rotar_estado.start()
    except Exception:
        pass
    try:
        avisar_miembros_identificacion.start()
    except Exception:
        pass
    try:
        keep_alive.start()
    except Exception:
        pass
    try:
        ranking_task.start()
    except Exception:
        pass

    # Enviar anuncio embed (sin staff)
    try:
        await enviar_anuncio()
    except Exception:
        pass

    # Botones y vistas
    # Identificación (canal de identificación)
    canal_identificacion = bot.get_channel(CANAL_IDENTIFICACION)
    if canal_identificacion:
        try:
            view_ident = View(timeout=None)
            btn_ident = Button(label="📝 Identifícate como mecánico", style=discord.ButtonStyle.green)
            async def ident_callback(interaction: discord.Interaction):
                await interaction.response.send_modal(IdentificacionModal())
            btn_ident.callback = ident_callback
            view_ident.add_item(btn_ident)
            await canal_identificacion.send(
                "Haz click en el botón para identificarte y rellenar el formulario de mecánico:",
                view=view_ident
            )
        except Exception:
            pass

    # Turnos (canal de turnos)
    canal_turnos = bot.get_channel(CANAL_TURNOS)
    if canal_turnos:
        try:
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
                # Si tenía tuneo sin finalizar lo añadimos al turno
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
            button_finalizar_turno.callback = finalizar_turno_callback
            view_turno.add_item(button_finalizar_turno)

            await canal_turnos.send("Pulsa los botones para gestionar tu turno:", view=view_turno)
        except Exception:
            pass

    # Tuneos (canal de tuneos)
    canal_tuneos = bot.get_channel(CANAL_TUNEOS)
    if canal_tuneos:
        try:
            view_tuneos = View(timeout=None)
            # Botones por cada tuneo
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
                # sumar al turno
                if uid in turnos_activos:
                    turnos_activos[uid]["dinero"] += dinero_tuneo
                if uid not in historial_tuneos:
                    historial_tuneos[uid] = {"dinero_total": 0, "tuneos": 0, "detalle": []}
                historial_tuneos[uid]["dinero_total"] += dinero_tuneo
                historial_tuneos[uid]["tuneos"] += 1
                historial_tuneos[uid]["detalle"].append(
                    (datetime.now(zona), dinero_tuneo, "Tuneo completado")
                )
                # Premio/Notificación para milestones -> lo enviamos al canal de ranking (visibilidad para mecánicos)
                try:
                    if historial_tuneos[uid]["tuneos"] in [50, 100, 200]:
                        canal = bot.get_channel(CANAL_RANKING)
                        if canal:
                            await canal.send(
                                f"🎉 ¡Felicidades <@{uid}>! Has alcanzado {historial_tuneos[uid]['tuneos']} tuneos, premio disponible 🎁."
                            )
                except Exception:
                    pass
                await interaction.followup.send(
                    f"✅ Tuneo finalizado. Dinero: ${dinero_tuneo:,} registrado como 1 tuneo.",
                    ephemeral=True
                )
            button_finalizar_tuneo.callback = finalizar_tuneo_callback
            view_tuneos.add_item(button_finalizar_tuneo)

            await canal_tuneos.send("Pulsa los botones para registrar tus tuneos y finalizar cada tuneo:", view=view_tuneos)
        except Exception:
            pass

    # Historial total: botón en canal de turnos (solo usuarios con roles de historial pueden verlo)
    if canal_turnos:
        try:
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
            await canal_turnos.send("Pulsa el botón para ver el historial completo de tuneos (solo roles autorizados):", view=view_historial)
        except Exception:
            pass

# ------------------------------
# Ejecutar bot
# ------------------------------
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("ERROR: La variable de entorno DISCORD_TOKEN no está configurada.")
    else:
        bot.run(TOKEN)
