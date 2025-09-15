import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
from datetime import datetime, timedelta
import pytz
import os
import itertools
import matplotlib.pyplot as plt
import io
import json
import asyncio
import traceback

# ==============================
# Overspeed RP - Bot reestructurado
# - Mantiene exactamente las mismas funcionalidades que el script original
# - Comentarios añadidos para explicar cada bloque
# - Cambios pedidos:
#   * El "historial completo" se enviará SOLO al canal de staff (configurable)
#   * En el embed de anuncio se ha eliminado la sección del "comando especial"
#   * Añadido comando `!anunciar` para crear anuncios embed desde el chat
# ==============================

# ------------------------------
# Configuración general / constantes
# ------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
zona = pytz.timezone("Europe/Madrid")

# ------------------------------
# Precios de los tuneos (sin cambios)
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

# Roles con permiso para ver historial / usar comandos administrativos
ROLES_HISTORIAL_TOTAL = [
    1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425,
    1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423,
    1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882,
    1415954460202766386
]

ROL_PROPIETARIO = 1410548111788740620  # Solo este rol puede usar !cambiarrol
ROL_MIEMBRO = 1387524774485299391      # Para avisos DM

# Prefijos que se aplican al apodo según rol (sin cambios)
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
# Canales (ACTUALIZA ESTOS VALORES si es necesario)
# - CANAL_IDENTIFICACION: canal donde hay botón para identificarse
# - CANAL_TURNOS: canal con botones de inicio/fin turno y historial
# - CANAL_TUNEOS: canal con botones de tuneos
# - CANAL_RANKING: canal donde se publican rankings
# - CANAL_KEEPALIVE: canal para pings keep-alive
# - CANAL_ANUNCIOS: canal por defecto donde enviar anuncios
# - CANAL_STAFF: canal del staff donde enviar el historial completo (DEBE CONFIGURARSE)
# - CANAL_RESULTADO_IDENTIFICACION: canal donde se envía el resultado de la identificación
CANAL_IDENTIFICACION = 1416880543122849802
ROLE_APRENDIZ = 1385301435456950390
ROLE_OVERSPEED = 1387571297705394250
CANAL_TURNOS = 1415949790545711236
CANAL_TUNEOS = 1415963375485321226
CANAL_RANKING = 1416021337519947858
CANAL_KEEPALIVE = 1387055864866799637
CANAL_ANUNCIOS = 1387551821224214839
CANAL_RESULTADO_IDENTIFICACION = 1417250457163665418


CANAL_STAFF = 1415964136550043689 
CANAL_LOGS = 1417250932386959441

# ------------------------------
# Estado runtime (estructuras de datos in-memory)
# ------------------------------
turnos_activos = {}      # user_id -> {"dinero": int, "inicio": datetime}
tuneos_activos = {}      # user_id -> {"dinero": int}
historial_tuneos = {}    # user_id -> {"dinero_total": int, "tuneos": int, "detalle": list}
avisados_identificacion = set()

# ------------------------------
# Estados rotativos del bot (actividad mostrada)
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

# ------------------------------
# Helpers (funciones utilitarias)
# ------------------------------

def has_any_role_by_id(member: discord.Member, role_ids: list) -> bool:
    """Comprueba si un miembro tiene alguno de los roles indicados (por id)."""
    try:
        return any(role.id in role_ids for role in member.roles)
    except Exception:
        return False


def safe_get_channel(channel_id: int):
    """Devuelve el canal si existe o None si no existe o si channel_id es None."""
    if not channel_id:
        return None
    return bot.get_channel(channel_id)


async def safe_send_interaction(interaction: discord.Interaction, content: str, *, ephemeral: bool = True):
    """Envía un mensaje respondiendo a una interacción de forma robusta.

    Intentos en orden:
      1. interaction.response.send_message (si no se ha respondido)
      2. interaction.followup.send
      3. interaction.channel.send
      4. interaction.user.send (DM)

    Atrapa discord.NotFound (webhook eliminado) y otros errores para evitar que la excepción propague.
    """
    try:
        if not interaction.response.is_done:
            # ephemeral messages can't be deleted later; return None
            await interaction.response.send_message(content, ephemeral=ephemeral)
            return None
        # response ya fue usada, intentar followup
        try:
            msg = await interaction.followup.send(content, ephemeral=ephemeral)
            return msg
        except discord.NotFound:
            # webhook de interacción desconocido; caemos a fallback
            pass
        except Exception:
            # cualquier otro error al hacer followup, intentamos fallback
            pass

        # fallback a enviar en canal público
        try:
            if interaction.channel:
                msg = await interaction.channel.send(content)
                return msg
        except Exception:
            pass

        # último recurso: DM al usuario
        try:
            msg = await interaction.user.send(content)
            return msg
        except Exception:
            pass
    except Exception:
        # No podemos hacer mucho más; intentar DM
        try:
            msg = await interaction.user.send(content)
            return msg
        except Exception:
            return None
    return None

# ------------------------------
# Tareas periódicas
# ------------------------------
@tasks.loop(minutes=10)
async def rotar_estado():
    """Rota la actividad del bot cada X minutos y cuenta mecánicos activos."""
    mec_activos = 0
    for guild in bot.guilds:
        for miembro in guild.members:
            try:
                if any(role.id in ROLES_TUNEO for role in miembro.roles):
                    mec_activos += 1
            except Exception:
                continue
    estado = next(estados)
    nombre_estado = getattr(estado, "name", None) or getattr(estado, "type", "Mecánicos")
    try:
        await bot.change_presence(activity=discord.Game(f"{nombre_estado} | Mecánicos activos: {mec_activos}"))
    except Exception:
        await bot.change_presence(activity=discord.Game(f"Mecánicos activos: {mec_activos}"))


@tasks.loop(hours=1)
async def avisar_miembros_identificacion():
    """Envía un DM a miembros sin identificar para recordarles que deben usar el canal de identificación."""
    for guild in bot.guilds:
        rol_miembro = guild.get_role(ROL_MIEMBRO)
        if rol_miembro is None:
            continue
        for miembro in rol_miembro.members:
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


@tasks.loop(minutes=10)
async def keep_alive():
    """Pequeño ping para mantener el bot activo en hosting que necesite actividad periódica."""
    canal = safe_get_channel(CANAL_KEEPALIVE)
    if canal:
        try:
            await canal.send("💤 Ping para mantener activo el bot.", delete_after=2)
        except Exception:
            pass


@tasks.loop(hours=24)
async def ranking_task():
    """Publica ranking semanal (domingo) y ranking mensual (cuando cambia mes)."""
    ahora = datetime.now(zona)
    canal = safe_get_channel(CANAL_RANKING)
    if canal is None:
        return
    try:
        # Ranking semanal (domingo)
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
# Modal de identificación (exactamente igual que antes, pero dentro de la estructura)
# ------------------------------
class IdentificacionModal(Modal, title="Identificación de mecánico"):
    nombre_ic = TextInput(label="Nombre IC", placeholder="Ej: John Doe", max_length=32)
    id_ic = TextInput(label="ID IC", placeholder="Ej: 12345", max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Evitar doble identificación si el usuario ya tiene el rol y apodo de aprendiz
            try:
                rol_aprendiz = interaction.guild.get_role(ROLE_APRENDIZ) if interaction.guild else None
                if rol_aprendiz and rol_aprendiz in interaction.user.roles and interaction.user.display_name.startswith("🧰 APR"):
                    # responder y salir
                    await safe_send_interaction(interaction, "⚠️ Ya estás identificado.")
                    return
            except Exception:
                # si algo falla con la comprobación, seguimos con la identificación normal
                pass

            nuevo_apodo = f"🧰 APR | {self.nombre_ic.value} | {self.id_ic.value}"
            canal_identificacion = None
            try:
                canal_identificacion = interaction.guild.get_channel(CANAL_RESULTADO_IDENTIFICACION)
            except Exception:
                canal_identificacion = None

            try:
                await interaction.user.edit(nick=nuevo_apodo)
                if canal_identificacion:
                    try:
                        await canal_identificacion.send(
                            f"✅ {interaction.user.mention} identificado correctamente como `{nuevo_apodo}`."
                        )
                    except Exception:
                        pass
            except discord.Forbidden:
                await safe_send_interaction(interaction, "⚠️ No tengo permisos para cambiar tu apodo.")
                if canal_identificacion:
                    try:
                        await canal_identificacion.send(
                            f"❌ Error al identificar a {interaction.user.mention}: No tengo permisos para cambiar el apodo."
                        )
                    except Exception:
                        pass
                return

            # Añadir roles de aprendiz y overspeed
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

            # Registrar la identificación en un thread privado del canal de identificación (si existe)
            try:
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
                            msg = await thread.send(f"{interaction.user.mention} identificado como: **{nuevo_apodo}**")
                            await msg.add_reaction("✅")
                        except Exception:
                            pass
            except Exception:
                # no bloqueamos si falla el thread
                pass

            # Responder al usuario indicando éxito
            await safe_send_interaction(interaction, f"✅ Identificación completada. Apodo cambiado a: {nuevo_apodo}")
        except Exception as e:
            # Registrar el error en canal de logs si está configurado
            tb = traceback.format_exc()
            canal_logs = safe_get_channel(CANAL_LOGS)
            if canal_logs:
                try:
                    await canal_logs.send(f"❌ Error en IdentificacionModal.on_submit para <@{interaction.user.id}>: {e}\n```{tb[:1900]}```")
                except Exception:
                    pass
            # Además guardamos el traceback en un archivo local para diagnóstico
            try:
                with open(os.path.join(os.path.dirname(__file__), 'ident_errors.log'), 'a') as lf:
                    lf.write(f"[{datetime.now(zona)}] Error en IdentificacionModal.on_submit para {interaction.user.id}: {e}\n{tb}\n---\n")
            except Exception:
                pass
            # Asegurar que el usuario recibe un mensaje de error amigable
            try:
                await safe_send_interaction(interaction, "❌ Algo salió mal, inténtalo de nuevo. Si el problema persiste, contacta con un administrador.")
            except Exception:
                # si ni siquiera podemos notificar al usuario, solo ignoramos
                pass

# ------------------------------
# Listener: borrar mensajes que escriban en el canal de identificación
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
# Función para enviar anuncio embed (modificada: se quita la sección del "comando especial")
# ------------------------------
async def enviar_anuncio():
    canal = safe_get_channel(CANAL_ANUNCIOS)
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

    embed.set_footer(text="🔧 Overspeed RP | Taller Oficial")
    try:
        await canal.send(embed=embed)
    except Exception:
        pass

# ------------------------------
# Comandos de texto existentes (historial, borrar, cambiarrol)
# - No se cambian sus permisos originales
# ------------------------------
@bot.command()
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def historial(ctx):
    """Muestra el historial completo de tuneos en un embed bonito."""
    if not historial_tuneos:
        embed = discord.Embed(
            title="📋 Historial de tuneos",
            description="No hay tuneos registrados.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    lines = []
    for uid, datos in historial_tuneos.items():
        # intentar convertir a int y buscar miembro en el guild
        try:
            uid_int = int(uid)
        except Exception:
            uid_int = uid
        miembro = ctx.guild.get_member(uid_int) if ctx.guild else None
        if miembro:
            apodo = miembro.display_name
        else:
            rol = datos.get("rol", "")
            nombre = datos.get("nombre", "")
            if rol and nombre:
                apodo = f"{rol} | {nombre}"
            elif nombre:
                apodo = nombre
            else:
                apodo = str(uid)
        tuneos = datos.get("tuneos", 0)
        lines.append(f"{apodo} | {uid}: {tuneos} tuneos")

    embed = discord.Embed(
        title="📋 Historial completo de tuneos",
        description="\n".join(lines),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)


@bot.command()
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def borrar(ctx, cantidad: int):
    deleted = await ctx.channel.purge(limit=cantidad + 1)
    embed = discord.Embed(
        title="🧹 Mensajes borrados",
        description=f"Se borraron {len(deleted)-1 if len(deleted)>0 else 0} mensajes.",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed, delete_after=5)


@bot.command()
async def cambiarrol(ctx, miembro: discord.Member, id_rol: int):
    """Cambia el rol y apodo de un usuario (solo propietario)."""
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
            canal_logs = safe_get_channel(CANAL_LOGS)
            if canal_logs:
                await canal_logs.send(
                    f"🔄 {ctx.author.mention} ha cambiado el rol de {miembro.mention} a {rol_obj.mention}.\nNuevo apodo: `{nuevo_apodo}`"
                )
        except discord.Forbidden:
            await ctx.send("⚠️ No tengo permisos para cambiar el apodo de ese usuario.")
    else:
        await ctx.send("⚠️ El apodo de este usuario no tiene el formato esperado. Formato esperado: `[emoji] ROL | Nombre | ID`")

@bot.command()
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def despedir(ctx, miembro: discord.Member, *, razon="No especificada"):
    if ctx.author == miembro:
        embed = discord.Embed(
            title="❌ Acción no permitida",
            description="No puedes despedirte a ti mismo.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    try:
        await miembro.kick(reason=razon)
        embed = discord.Embed(
            title="🚫 Usuario despedido",
            description=f"{miembro.mention} ha sido despedido del servidor.\nMotivo: {razon}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        canal_logs = safe_get_channel(CANAL_LOGS)
        if canal_logs:
            embed_log = discord.Embed(
                title="🚫 Despido registrado",
                description=f"{miembro.mention} fue despedido por {ctx.author.mention}.\nMotivo: {razon}",
                color=discord.Color.red()
            )
            await canal_logs.send(embed=embed_log)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error al despedir",
            description=f"No se pudo despedir a {miembro.mention}. Error: {e}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        canal_logs = safe_get_channel(CANAL_LOGS)
        if canal_logs:
            embed_log = discord.Embed(
                title="❌ Error al despedir",
                description=f"Error al despedir a {miembro.mention} por {ctx.author.mention}: {e}",
                color=discord.Color.red()
            )
            await canal_logs.send(embed=embed_log)

# ------------------------------
# Nuevo: comando para crear anuncios embed desde chat
# Uso:
#  - Modo por defecto (envía a CANAL_ANUNCIOS):
#      !anunciar Titulo | Descripción larga del anuncio
#  - Modo especificando canal (primer bloque solo números => canal_id):
#      !anunciar 123456789012345678 | Titulo | Descripción
# Permisos: roles listados en ROLES_HISTORIAL_TOTAL
# ------------------------------
@bot.command(name="anunciar")
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def anunciar(ctx, *, args: str):
    """Crea y envía un embed de anuncio. Ver comentarios arriba para el uso."""
    parts = [p.strip() for p in args.split('|', 2)]
    if len(parts) < 2:
        return await ctx.send("Uso: `!anunciar [canal_id] | Titulo | Descripción`  (si no pones canal_id, se usa el canal por defecto).")

    # Si el primer bloque parece un ID de canal (solo dígitos), lo usamos
    if parts[0].isdigit() and len(parts) > 1 and len(parts[0]) > 5:
        try:
            canal_id = int(parts[0])
        except Exception:
            return await ctx.send("ID de canal inválido.")
        if len(parts) < 3:
            return await ctx.send("Si especificas canal_id, usa: canal_id | Titulo | Descripción")
        title = parts[1]
        description = parts[2]
        canal = safe_get_channel(canal_id)
        if canal is None:
            return await ctx.send("No encuentro ese canal. Asegúrate de que el ID está correcto y que el bot puede ver el canal.")
    else:
        # usar canal por defecto
        canal = safe_get_channel(CANAL_ANUNCIOS)
        title = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        if canal is None:
            return await ctx.send("Canal de anuncios por defecto no configurado en el bot.")

    embed = discord.Embed(title=f"📢 {title}", description=description, color=discord.Color.orange())
    try:
        await canal.send(embed=embed)
        await ctx.send("✅ Anuncio enviado.", delete_after=5)
    except Exception:
        await ctx.send("❌ Error al enviar el anuncio. Revisa permisos del bot y del canal.")

# ------------------------------
# Función que construye y envía las vistas con botones (identificación, turnos, tuneos, historial)
# - Esta función encapsula la lógica que antes estaba en on_ready para crear/adjuntar vistas
# - Mantiene exactamente las mismas interacciones y mensajes de respuesta que el script original
# ------------------------------
async def construir_y_enviar_vistas():
    # Identificación
    canal_identificacion = safe_get_channel(CANAL_IDENTIFICACION)
    if canal_identificacion:
        try:
            view_ident = View(timeout=None)
            btn_ident = Button(label="📝 Identifícate como mecánico", style=discord.ButtonStyle.green)

            async def ident_callback(interaction: discord.Interaction):
                # Comprobar si ya está identificado para evitar proceso innecesario
                try:
                    rol_aprendiz = interaction.guild.get_role(ROLE_APRENDIZ) if interaction.guild else None
                    if rol_aprendiz and rol_aprendiz in interaction.user.roles and interaction.user.display_name.startswith("🧰 APR"):
                        await safe_send_interaction(interaction, "⚠️ Ya estás identificado.")
                        return
                except Exception:
                    pass

                # Informar al usuario (ephemeral) que debe responder en el canal y que sus mensajes serán borrados
                msg = await safe_send_interaction(interaction, "Por favor responde en este canal con tu **NOMBRE IC**. Tu mensaje será eliminado inmediatamente después de recibirlo.")

                def check_nombre(m: discord.Message):
                    return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

                try:
                    msg_nombre = await bot.wait_for('message', check=check_nombre, timeout=120.0)
                except Exception:
                    await safe_send_interaction(interaction, "⏱️ Tiempo agotado para responder con el nombre. Intenta de nuevo.")
                    return

                nombre_ic = msg_nombre.content.strip()
                # intentar borrar el mensaje del usuario para que no quede en el canal
                try:
                    await msg_nombre.delete()
                except Exception:
                    pass

                msg2 = await safe_send_interaction(interaction, "✅ Nombre recibido.")
                # intentar borrar el mensaje del bot para mantener el canal limpio
                try:
                    if msg2 is not None:
                        await asyncio.sleep(5)
                        await msg2.delete()
                except Exception:
                    pass

                # Pedir ID IC de forma similar
                msg3 = await safe_send_interaction(interaction, "Ahora responde en este canal con tu **ID IC**. También se borrará tu mensaje.")
                try:
                    if msg3 is not None:
                        await asyncio.sleep(5)
                        await msg3.delete()
                except Exception:
                    pass

                def check_id(m: discord.Message):
                    return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

                try:
                    msg_idic = await bot.wait_for('message', check=check_id, timeout=120.0)
                except Exception:
                    await safe_send_interaction(interaction, "⏱️ Tiempo agotado para responder con el ID. Intenta de nuevo.")
                    return

                id_ic = msg_idic.content.strip()
                try:
                    await msg_idic.delete()
                except Exception:
                    pass

                nuevo_apodo = f"🧰 APR | {nombre_ic} | {id_ic}"

                # Intentar aplicar apodo y roles
                try:
                    await interaction.user.edit(nick=nuevo_apodo)
                except Exception:
                    await safe_send_interaction(interaction, "⚠️ No pude cambiar tu apodo. Revisa permisos del bot.")

                try:
                    rol1 = interaction.guild.get_role(ROLE_APRENDIZ)
                    rol2 = interaction.guild.get_role(ROLE_OVERSPEED)
                    if rol1:
                        await interaction.user.add_roles(rol1)
                    if rol2:
                        await interaction.user.add_roles(rol2)
                except Exception:
                    await safe_send_interaction(interaction, "⚠️ No pude asignarte uno o más roles. Contacta con un administrador.")

                # Registrar en canal de resultado
                try:
                    canal_res = interaction.guild.get_channel(CANAL_RESULTADO_IDENTIFICACION)
                    if canal_res:
                        await canal_res.send(f"✅ {interaction.user.mention} identificado correctamente como `{nuevo_apodo}`.")
                except Exception:
                    pass

                msg_fin = await safe_send_interaction(interaction, f"✅ Identificación completada. Apodo cambiado a: {nuevo_apodo}")
                try:
                    if msg_fin is not None:
                        await asyncio.sleep(5)
                        await msg_fin.delete()
                except Exception:
                    pass

            btn_ident.callback = ident_callback
            view_ident.add_item(btn_ident)
            await canal_identificacion.send(
                "Haz click en el botón para identificarte y rellenar el formulario de mecánico:",
                view=view_ident
            )
        except Exception:
            pass

    # Turnos (iniciar / finalizar / historial total)
    canal_turnos = safe_get_channel(CANAL_TURNOS)
    canal_staff = safe_get_channel(CANAL_STAFF)
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

    # Tuneos
    canal_tuneos = safe_get_channel(CANAL_TUNEOS)
    if canal_tuneos:
        try:
            view_tuneos = View(timeout=None)

            for tuneo, precio in precios_tuneos.items():
                button = Button(label=f"{tuneo} (${precio:,})", style=discord.ButtonStyle.blurple)

                async def make_tuneo_callback(t=tuneo, p=precio):
                    async def tuneo_callback(interaction: discord.Interaction):
                        uid = interaction.user.id
                        await interaction.response.defer(ephemeral=True)
                        if uid not in turnos_activos:
                            return await interaction.followup.send("❌ No tienes un turno activo.", ephemeral=True)
                        if uid not in tuneos_activos:
                            tuneos_activos[uid] = {"dinero": 0}
                        tuneos_activos[uid]["dinero"] += p
                        total = tuneos_activos[uid]["dinero"]
                        await interaction.followup.send(f"🔧 Añadido {t}. Total tuneo: ${total:,}", ephemeral=True)
                    return tuneo_callback

                button.callback = await make_tuneo_callback()
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
                try:
                    if historial_tuneos[uid]["tuneos"] in [50, 100, 200]:
                        canal = safe_get_channel(CANAL_RANKING)
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

    # Historial total (antes se enviaba ephemerally al usuario; ahora el contenido se envía SOLO al CANAL_STAFF)
    if canal_staff:
        try:
            view_historial = View(timeout=None)
            button_historial = Button(label="📋 Historial Total", style=discord.ButtonStyle.gray)

            async def historial_callback(interaction: discord.Interaction):
                await interaction.response.defer(ephemeral=True)
                # comprobar permisos
                if not any(role.id in ROLES_HISTORIAL_TOTAL for role in interaction.user.roles):
                    await interaction.followup.send("❌ No tienes permiso para ver el historial completo.", ephemeral=True)
                    return
                if not historial_tuneos:
                    await interaction.followup.send("❌ No hay tuneos registrados.", ephemeral=True)
                    return

                canal_staff = safe_get_channel(CANAL_STAFF)
                if canal_staff is None:
                    # Si no está configurado el canal de staff, avisamos al usuario que lo configure
                    await interaction.followup.send("⚠️ El canal de staff no está configurado. Contacta con el administrador.", ephemeral=True)
                    return

                # Construimos el embed del historial usando apodos si están disponibles
                lines = []
                for uid, datos in historial_tuneos.items():
                    try:
                        uid_int = int(uid)
                    except Exception:
                        uid_int = uid
                    miembro = interaction.guild.get_member(uid_int) if interaction.guild else None
                    if miembro:
                        apodo = miembro.display_name
                    else:
                        rol = datos.get("rol", "")
                        nombre = datos.get("nombre", "")
                        if rol and nombre:
                            apodo = f"{rol} | {nombre}"
                        elif nombre:
                            apodo = nombre
                        else:
                            apodo = str(uid)
                    tuneos = datos.get("tuneos", 0)
                    lines.append(f"{apodo} — {tuneos} tuneos")

                embed_hist = discord.Embed(
                    title="📋 Historial completo de tuneos (staff)",
                    description="\n".join(lines),
                    color=discord.Color.blue()
                )
                try:
                    await canal_staff.send(embed=embed_hist)
                    await interaction.followup.send("✅ Historial enviado al canal de staff.", ephemeral=True)
                except Exception:
                    await interaction.followup.send("❌ No pude enviar el historial al canal de staff (revisa permisos).", ephemeral=True)

            button_historial.callback = historial_callback
            view_historial.add_item(button_historial)
            await canal_turnos.send("Pulsa el botón para ver el historial completo de tuneos (solo roles autorizados):", view=view_historial)
        except Exception:
            pass

# ------------------------------
# on_ready: arranca tareas y construye vistas
# ------------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    # Iniciar tareas (si ya están iniciadas, .start() lanza excepción y pasamos)
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
    try:
        backup_task.start()
    except Exception:
        pass

    # Enviar anuncio embed inicial (sin mencionar comando especial)
    try:
        await enviar_anuncio()
    except Exception:
        pass

    # Construir y enviar las vistas con botones a sus canales
    try:
        await construir_y_enviar_vistas()
    except Exception:
        pass

@bot.command()
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def dashboard(ctx):
    if not historial_tuneos:
        embed = discord.Embed(
            title="Sin datos",
            description="No hay datos de tuneos registrados.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Config: mostrar top N mecánicos (por defecto 10)
    TOP_N = 10
    # Construir lista ordenada por tuneos desc
    items = sorted(historial_tuneos.items(), key=lambda x: x[1].get('tuneos', 0), reverse=True)
    top_items = items[:TOP_N]

    nombres = []
    datos = []
    for uid, datos_v in top_items:
        try:
            uid_int = int(uid)
        except Exception:
            uid_int = uid
        miembro = ctx.guild.get_member(uid_int) if ctx.guild else None
        if miembro:
            nombre = miembro.display_name
        else:
            nombre = datos_v.get('nombre') or str(uid)
        nombres.append(nombre)
        datos.append(datos_v.get('tuneos', 0))

    # Si no hay datos dentro de top_items (caso raro), avisar
    if not datos:
        embed = discord.Embed(title="Sin datos", description="No hay tuneos para mostrar.", color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Gráfico más profesional: si seaborn está disponible lo usamos, si no fallback a ggplot
    try:
        import seaborn as sns
        sns.set_theme(style='darkgrid')
    except Exception:
        try:
            plt.style.use('ggplot')
        except Exception:
            try:
                plt.style.use('default')
            except Exception:
                pass
    fig, ax = plt.subplots(figsize=(10, max(4, 0.6 * len(nombres))))
    y_pos = range(len(nombres))

    # gradiente de color simple
    cmap = plt.get_cmap('viridis')
    colors = [cmap(i / max(1, len(nombres)-1)) for i in range(len(nombres))]

    ax.barh(y_pos, datos, color=colors)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(nombres)
    ax.invert_yaxis()
    ax.set_xlabel('Tuneos')
    ax.set_title('Top mecánicos por tuneos')

    # Annotate counts
    for i, v in enumerate(datos):
        ax.text(v + max(1, int(max(datos) * 0.01)), i, str(v), va='center')

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close(fig)

    # Embed con resumen
    total_tuneos = sum(v.get('tuneos', 0) for _, v in historial_tuneos.items())
    top1 = nombres[0] if nombres else 'N/A'
    embed = discord.Embed(
        title="📊 Dashboard de actividad",
        description=f"Total de tuneos registrados: **{total_tuneos}**\nTop 1: **{top1}**",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, file=discord.File(buf, filename="dashboard.png"))

# ------------------------------
# Backup: guardar historial y configuración cada 6 horas
# ------------------------------
@tasks.loop(hours=6)
async def backup_task():
    """Guarda backup del historial y configuración cada 6 horas."""
    backup = {
        "historial_tuneos": historial_tuneos,
        "turnos_activos": turnos_activos,
        "tuneos_activos": tuneos_activos
    }
    try:
        with open("/workspaces/Bots-Discord/backup.json", "w") as f:
            json.dump(backup, f, default=str)
    except Exception as e:
        canal_logs = safe_get_channel(CANAL_LOGS)
        if canal_logs:
            await canal_logs.send(f"❌ Error al guardar backup: {e}")

# ------------------------------
# Comandos para guardar y cargar datos manualmente
# ------------------------------
import json
import os

BACKUP_PATH = os.path.join(os.path.dirname(__file__), 'backup.json')

@bot.command()
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def guardar(ctx):
    """Guarda manualmente los datos actuales en backup.json."""
    backup = {
        "historial_tuneos": historial_tuneos,
        "turnos_activos": turnos_activos,
        "tuneos_activos": tuneos_activos
    }
    try:
        with open(BACKUP_PATH, "w") as f:
            json.dump(backup, f, default=str)
        embed = discord.Embed(
            title="✅ Datos guardados",
            description="Los datos se han guardado correctamente.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error al guardar",
            description=str(e),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command()
@commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
async def cargar(ctx):
    """Carga los datos guardados desde backup.json."""
    global historial_tuneos, turnos_activos, tuneos_activos
    try:
        with open(BACKUP_PATH, "r") as f:
            backup = json.load(f)
        historial_tuneos = backup.get("historial_tuneos", {})
        turnos_activos = backup.get("turnos_activos", {})
        tuneos_activos = backup.get("tuneos_activos", {})
        embed = discord.Embed(
            title="✅ Datos cargados",
            description="Los datos se han restaurado correctamente.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error al cargar",
            description=str(e),
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# ------------------------------
# Comando de identificación manual (ejemplo simple, sin botones)
# ------------------------------
@bot.command()
async def identificar(ctx):
    """Ejemplo de verificación antes de identificar."""
    aprendiz_rol = ctx.guild.get_role(ROLE_APRENDIZ)
    if aprendiz_rol in ctx.author.roles and ctx.author.display_name.startswith("🧰 APR"):
        embed = discord.Embed(
            title="✅ Ya estás identificado",
            description="Ya tienes el rol de aprendiz y el apodo configurado.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return
    # Aquí iría el resto de la lógica de identificación, si es necesario

# ------------------------------
# Ejecutar bot
# ------------------------------
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("ERROR: La variable de entorno DISCORD_TOKEN no está configurada.")
    else:
        bot.run(TOKEN)
