import discord
from discord.ui import Button, View
from datetime import datetime
import logging
import re

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
    PROMO_ROLE_ID,
    PROMO_NOTIFY_CHANNEL,
)
from utils.helpers import (
    safe_get_channel,
    turnos_activos,
    tuneos_activos,
    historial_tuneos,
    normalize_user_identity
)
from handlers.identification import handle_identification_channel

# Añadido: supabase service y logger
from utils.supabase_service import supabase_service

logger = logging.getLogger(__name__)


def _extract_legacy_id(display_name: str) -> str | None:
    """Extrae un posible ID legacy al final del apodo '... | 11895'"""
    if not display_name:
        return None
    m = re.search(r'\b(\d{3,12})\s*$', display_name)
    return m.group(1) if m else None


async def setup_views(bot: discord.Client):
    # Identificación
    canal_identificacion = safe_get_channel(bot, CANAL_IDENTIFICACION)
    if canal_identificacion:
        try:
            view_ident = View(timeout=None)
            btn_ident = Button(label="📝 Identifícate como mecánico", style=discord.ButtonStyle.green)

            async def ident_callback(interaction: discord.Interaction):
                # Usar la nueva función de identificación en canal
                bot = interaction.client
                user = interaction.user
                guild = interaction.guild
                canal_ident = interaction.channel

                try:
                    await interaction.response.defer(ephemeral=True)
                except Exception:
                    pass

                # Llamar a la función de identificación en canal
                success, message = await handle_identification_channel(bot, user, guild, canal_ident)
                
                if success:
                    await interaction.followup.send("✅ Identificación completada.", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ {message}", ephemeral=True)

            btn_ident.callback = ident_callback
            view_ident.add_item(btn_ident)
            msg = await canal_identificacion.send(
                "Haz clic en el botón para identificarte y rellenar el formulario de mecánico.\n"
                "Las preguntas aparecerán aquí mismo en el canal.",
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
                    # Guardar/actualizar en Supabase: crear usuario si no existe y aumentar contador
                    try:
                        server_id = str(interaction.guild.id) if interaction.guild else ""
                        rol = historial_tuneos[uid].get("rol", "")
                        target_user_id, clean_name = normalize_user_identity(interaction.user.display_name, uid)
                        nombre = historial_tuneos[uid].get("nombre") or clean_name
                        await supabase_service.create_or_update_user(
                            user_id=str(target_user_id),
                            nombre=nombre,
                            rol=rol,
                            server_id=server_id
                        )
                        success, prev, new = await supabase_service.increment_tuneo_count(str(target_user_id), server_id)
                        # Promotion logic
                        try:
                            member = interaction.guild.get_member(uid) if interaction.guild else None
                            promo_role = None
                            # Preferir role por ID (más fiable). Si PROMO_ROLE_ID no está configurado (>0), hacer fallback por nombre.
                            if interaction.guild and PROMO_ROLE_ID:
                                promo_role = interaction.guild.get_role(PROMO_ROLE_ID)
                            elif interaction.guild:
                                for r in interaction.guild.roles:
                                    if r.name.lower() == "promocionar":
                                        promo_role = r
                                        break
                            notify_channel = interaction.client.get_channel(PROMO_NOTIFY_CHANNEL)
                            if success:
                                if prev <= 20 and new > 20:
                                    # promote
                                    if member and promo_role:
                                        try:
                                            await member.add_roles(promo_role, reason="Reach >20 tuneos (auto)")
                                        except Exception:
                                            logger.exception("No se pudo añadir rol promocionar")
                                    if notify_channel:
                                        await notify_channel.send(f"🔼 Promoción: {interaction.user.mention} ha alcanzado {new} tuneos. Revisar para ascenso.")
                                elif prev > 20 and new <= 20:
                                    # demote
                                    if member and promo_role:
                                        try:
                                            await member.remove_roles(promo_role, reason="Tuneos reducidos <=20 (auto)")
                                        except Exception:
                                            logger.exception("No se pudo quitar rol promocionar")
                                    if notify_channel:
                                        await notify_channel.send(f"🔽 Degradación: {interaction.user.mention} ahora tiene {new} tuneos.")
                        except Exception:
                            logger.exception("Error aplicando reglas de promoción en finalizar_turno")
                    except Exception:
                        logger.exception("Error actualizando Supabase al finalizar turno con tuneo pendiente")

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

                # Guardar/actualizar en Supabase: crear usuario si no existe y aumentar contador
                try:
                    server_id = str(interaction.guild.id) if interaction.guild else ""
                    rol = historial_tuneos[uid].get("rol", "")
                    target_user_id, clean_name = normalize_user_identity(interaction.user.display_name, uid)
                    nombre = historial_tuneos[uid].get("nombre") or clean_name
                    await supabase_service.create_or_update_user(
                        user_id=str(target_user_id),
                        nombre=nombre,
                        rol=rol,
                        server_id=server_id
                    )
                    success, prev, new = await supabase_service.increment_tuneo_count(str(target_user_id), server_id)

                    # Promotion logic (same as above)
                    try:
                        member = interaction.guild.get_member(uid) if interaction.guild else None
                        promo_role = None
                        # Preferir role por ID (más fiable). Si PROMO_ROLE_ID no está configurado (>0), hacer fallback por nombre.
                        if interaction.guild and PROMO_ROLE_ID:
                            promo_role = interaction.guild.get_role(PROMO_ROLE_ID)
                        elif interaction.guild:
                            for r in interaction.guild.roles:
                                if r.name.lower() == "promocionar":
                                    promo_role = r
                                    break
                        notify_channel = interaction.client.get_channel(PROMO_NOTIFY_CHANNEL)
                        if success:
                            if prev <= 20 and new > 20:
                                if member and promo_role:
                                    try:
                                        await member.add_roles(promo_role, reason="Reach >20 tuneos (auto)")
                                    except Exception:
                                        logger.exception("No se pudo añadir rol promocionar")
                                if notify_channel:
                                    await notify_channel.send(f"🔼 Promoción: {interaction.user.mention} ha alcanzado {new} tuneos. Revisar para ascenso.")
                            elif prev > 20 and new <= 20:
                                if member and promo_role:
                                    try:
                                        await member.remove_roles(promo_role, reason="Tuneos reducidos <=20 (auto)")
                                    except Exception:
                                        logger.exception("No se pudo quitar rol promocionar")
                                if notify_channel:
                                    await notify_channel.send(f"🔽 Degradación: {interaction.user.mention} ahora tiene {new} tuneos.")
                    except Exception:
                        logger.exception("Error aplicando reglas de promoción en finalizar_tuneo")

                except Exception:
                    logger.exception("Error actualizando Supabase al finalizar tuneo")

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
    if canal_staff:
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
            await canal_staff.send(
                "Pulsa el botón para ver el historial completo de tuneos (solo roles autorizados):",
                view=view_historial,
            )
        except Exception:
            pass
