import discord
from discord.ui import Button, View
from datetime import datetime

from config.settings import ZONA
from config.constants import (
    CANAL_IDENTIFICACION,
    CANAL_TURNOS,
    CANAL_TUNEOS,
    CANAL_RANKING,
    CANAL_STAFF,
    ROLES_TUNEO,
    ROLES_HISTORIAL_TOTAL,
    PRECIOS_TUNEOS,
    ROLE_APRENDIZ,
    ROLE_OVERSPEED,
    CANAL_RESULTADO_IDENTIFICACION,
)
from utils.helpers import (
    safe_get_channel,
    safe_send_interaction,
    turnos_activos,
    tuneos_activos,
    historial_tuneos,
)


async def setup_views(bot: discord.Client):
    # Identificación
    canal_identificacion = safe_get_channel(bot, CANAL_IDENTIFICACION)
    if canal_identificacion:
        try:
            view_ident = View(timeout=None)
            btn_ident = Button(label="📝 Identifícate como mecánico", style=discord.ButtonStyle.green)

            async def ident_callback(interaction: discord.Interaction):
                # Avisa ephemerally y arranca conversación por DM
                try:
                    await interaction.response.defer(ephemeral=True)
                except Exception:
                    pass
                bot = interaction.client
                user = interaction.user
                guild = interaction.guild

                # Intentamos abrir DM
                try:
                    dm = await user.create_dm()
                    await dm.send(
                        "Hola! Vamos a completar tu identificación como mecánico.\n"
                        "Contesta a las siguientes preguntas. Puedes escribir 'cancelar' en cualquier momento para abortar."
                    )
                except Exception:
                    # No se pudo enviar DM
                    await interaction.followup.send(
                        "❌ No pude enviarte un mensaje directo. Activa tus MD e inténtalo de nuevo.",
                        ephemeral=True,
                    )
                    # Opcional: log al staff
                    canal_staff_local = safe_get_channel(bot, CANAL_STAFF)
                    if canal_staff_local:
                        try:
                            await canal_staff_local.send(
                                f"❌ No pude iniciar DM con {user.mention} para identificación. Tiene los MD desactivados."
                            )
                        except Exception:
                            pass
                    return

                def check_author_dm(m: discord.Message):
                    return m.author.id == user.id and m.channel.id == dm.id

                # Pregunta 1: Nombre IC
                try:
                    await dm.send("¿Cuál es tu Nombre IC? (máx 32 caracteres)")
                    nombre_msg = await bot.wait_for("message", timeout=120, check=check_author_dm)
                    nombre = nombre_msg.content.strip()
                    if nombre.lower() == "cancelar":
                        await dm.send("Operación cancelada.")
                        await interaction.followup.send("Operación cancelada.", ephemeral=True)
                        return
                    if len(nombre) == 0 or len(nombre) > 32:
                        await dm.send("❌ Nombre inválido. Vuelve a intentarlo con el botón del canal.")
                        await interaction.followup.send("❌ Nombre inválido.", ephemeral=True)
                        return
                except Exception:
                    await dm.send("⏰ Tiempo agotado. Vuelve a intentarlo con el botón del canal.")
                    await interaction.followup.send("⏰ Tiempo agotado.", ephemeral=True)
                    return

                # Pregunta 2: ID IC
                try:
                    await dm.send("¿Cuál es tu ID IC? (máx 10 caracteres, sólo números)")
                    id_msg = await bot.wait_for("message", timeout=120, check=check_author_dm)
                    id_ic = id_msg.content.strip()
                    if id_ic.lower() == "cancelar":
                        await dm.send("Operación cancelada.")
                        await interaction.followup.send("Operación cancelada.", ephemeral=True)
                        return
                    if len(id_ic) == 0 or len(id_ic) > 10 or not id_ic.isdigit():
                        await dm.send("❌ ID inválido. Vuelve a intentarlo con el botón del canal.")
                        await interaction.followup.send("❌ ID inválido.", ephemeral=True)
                        return
                except Exception:
                    await dm.send("⏰ Tiempo agotado. Vuelve a intentarlo con el botón del canal.")
                    await interaction.followup.send("⏰ Tiempo agotado.", ephemeral=True)
                    return

                # Confirmación obtenida, procedemos a aplicar cambios
                nuevo_apodo = f"🧰 APR | {nombre} | {id_ic}"
                canal_resultado = guild.get_channel(CANAL_RESULTADO_IDENTIFICACION) if guild else None
                try:
                    await user.edit(nick=nuevo_apodo)
                    if canal_resultado:
                        try:
                            await canal_resultado.send(
                                f"✅ {user.mention} identificado correctamente como `{nuevo_apodo}`."
                            )
                        except Exception:
                            pass
                except discord.Forbidden:
                    await dm.send("⚠️ No tengo permisos para cambiar tu apodo. Contacta con un administrador.")
                    if canal_resultado:
                        try:
                            await canal_resultado.send(
                                f"❌ Error al identificar a {user.mention}: No tengo permisos para cambiar el apodo."
                            )
                        except Exception:
                            pass
                    await interaction.followup.send("❌ No tengo permisos para cambiar tu apodo.", ephemeral=True)
                    return
                except Exception:
                    # Error genérico
                    if canal_resultado:
                        try:
                            await canal_resultado.send(
                                f"❌ Error no esperado al identificar a {user.mention} (cambio de apodo)."
                            )
                        except Exception:
                            pass
                    await interaction.followup.send("❌ Ocurrió un error. Intenta más tarde.", ephemeral=True)
                    return

                # Añadir roles
                try:
                    rol_aprendiz = guild.get_role(ROLE_APRENDIZ) if guild else None
                    rol_overspeed = guild.get_role(ROLE_OVERSPEED) if guild else None
                    if rol_aprendiz:
                        try:
                            await user.add_roles(rol_aprendiz)
                        except Exception:
                            pass
                    if rol_overspeed:
                        try:
                            await user.add_roles(rol_overspeed)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Registrar en hilo del canal de identificación (opcional)
                try:
                    canal_ident = guild.get_channel(CANAL_IDENTIFICACION)
                    thread_name = "Identificaciones Mecánicos"
                    thread = None
                    if canal_ident:
                        for th in canal_ident.threads:
                            if th.name == thread_name:
                                thread = th
                                break
                        if thread is None:
                            try:
                                thread = await canal_ident.create_thread(
                                    name=thread_name,
                                    type=discord.ChannelType.private_thread,
                                    invitable=False,
                                )
                                await thread.edit(invitable=False)
                            except Exception:
                                thread = None
                        if thread:
                            try:
                                msg = await thread.send(f"{user.mention} identificado como: **{nuevo_apodo}**")
                                await msg.add_reaction("✅")
                            except Exception:
                                pass
                except Exception:
                    pass

                # Limpiar canal de identificación y dejar sólo el botón (mensaje pineado)
                try:
                    canal_ident = guild.get_channel(CANAL_IDENTIFICACION)
                    if canal_ident:
                        async for m in canal_ident.history(limit=100):
                            if not m.pinned:
                                try:
                                    await m.delete()
                                except Exception:
                                    pass
                except Exception:
                    pass

                try:
                    await dm.send(f"✅ Identificación completada. Apodo cambiado a: {nuevo_apodo}")
                except Exception:
                    pass
                await interaction.followup.send("✅ Identificación completada.", ephemeral=True)

            btn_ident.callback = ident_callback
            view_ident.add_item(btn_ident)
            msg = await canal_identificacion.send(
                "Haz clic en el botón para identificarte y rellenar el formulario de mecánico.\n"
                "Las respuestas y confirmaciones serán privadas por MD.",
                view=view_ident,
            )
            # Intentar pinear el mensaje del botón, para preservarlo en la limpieza
            try:
                await msg.pin()
            except Exception:
                pass
        except Exception:
            pass

    # Turnos
    canal_turnos = safe_get_channel(bot, CANAL_TURNOS)
    canal_staff = safe_get_channel(bot, CANAL_STAFF)
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
                turnos_activos[uid] = {"dinero": 0, "inicio": datetime.now(ZONA)}
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
                        (datetime.now(ZONA), dinero_tuneo, "Finalizado auto al cerrar turno")
                    )
                datos_turno = turnos_activos.pop(uid)
                total_dinero = datos_turno["dinero"]
                inicio = datos_turno["inicio"]
                duracion = datetime.now(ZONA) - inicio
                if uid not in historial_tuneos:
                    historial_tuneos[uid] = {"dinero_total": 0, "tuneos": 0, "detalle": []}
                historial_tuneos[uid]["dinero_total"] += total_dinero
                await interaction.followup.send(
                    f"✅ Turno finalizado. Total dinero acumulado: ${total_dinero:,}\n⏱️ Duración: {duracion}",
                    ephemeral=True,
                )

            button_finalizar_turno.callback = finalizar_turno_callback
            view_turno.add_item(button_finalizar_turno)

            await canal_turnos.send("Pulsa los botones para gestionar tu turno:", view=view_turno)
        except Exception:
            pass

    # Tuneos
    canal_tuneos = safe_get_channel(bot, CANAL_TUNEOS)
    if canal_tuneos:
        try:
            view_tuneos = View(timeout=None)

            for tuneo, precio in PRECIOS_TUNEOS.items():
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
                if uid in turnos_activos:
                    turnos_activos[uid]["dinero"] += dinero_tuneo
                if uid not in historial_tuneos:
                    historial_tuneos[uid] = {"dinero_total": 0, "tuneos": 0, "detalle": []}
                historial_tuneos[uid]["dinero_total"] += dinero_tuneo
                historial_tuneos[uid]["tuneos"] += 1
                historial_tuneos[uid]["detalle"].append((datetime.now(ZONA), dinero_tuneo, "Tuneo completado"))
                try:
                    if historial_tuneos[uid]["tuneos"] in [50, 100, 200]:
                        canal = safe_get_channel(bot, CANAL_RANKING)
                        if canal:
                            await canal.send(
                                f"🎉 ¡Felicidades <@{uid}>! Has alcanzado {historial_tuneos[uid]['tuneos']} tuneos, premio disponible 🎁."
                            )
                except Exception:
                    pass
                await interaction.followup.send(
                    f"✅ Tuneo finalizado. Dinero: ${dinero_tuneo:,} registrado como 1 tuneo.",
                    ephemeral=True,
                )

            button_finalizar_tuneo.callback = finalizar_tuneo_callback
            view_tuneos.add_item(button_finalizar_tuneo)

            await canal_tuneos.send(
                "Pulsa los botones para registrar tus tuneos y finalizar cada tuneo:", view=view_tuneos
            )
        except Exception:
            pass

    # Historial total al canal de staff
    if canal_staff and canal_turnos:
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

                canal_staff_local = safe_get_channel(bot, CANAL_STAFF)
                if canal_staff_local is None:
                    await interaction.followup.send(
                        "⚠️ El canal de staff no está configurado. Contacta con el administrador.",
                        ephemeral=True,
                    )
                    return

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
                    color=discord.Color.blue(),
                )
                try:
                    await canal_staff_local.send(embed=embed_hist)
                    await interaction.followup.send("✅ Historial enviado al canal de staff.", ephemeral=True)
                except Exception:
                    await interaction.followup.send(
                        "❌ No pude enviar el historial al canal de staff (revisa permisos).",
                        ephemeral=True,
                    )

            button_historial.callback = historial_callback
            view_historial.add_item(button_historial)
            await canal_turnos.send(
                "Pulsa el botón para ver el historial completo de tuneos (solo roles autorizados):",
                view=view_historial,
            )
        except Exception:
            pass
