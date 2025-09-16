import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import tasks

from config.constants import (
    ROLES_TUNEO,
    ROL_MIEMBRO,
    CANAL_KEEPALIVE,
    CANAL_RANKING,
)
from config.settings import ZONA
from config.constants import ESTADOS
from utils.helpers import historial_tuneos, avisados_identificacion, safe_get_channel
from utils.database import save_backup


def start_tasks(bot: discord.Client):
    try:
        rotar_estado.change_interval(minutes=10)
        rotar_estado.start(bot)
    except Exception:
        pass
    try:
        avisar_miembros_identificacion_task.change_interval(hours=1)
        avisar_miembros_identificacion_task.start(bot)
    except Exception:
        pass
    try:
        keep_alive_task.change_interval(minutes=10)
        keep_alive_task.start(bot)
    except Exception:
        pass
    try:
        ranking_task.change_interval(hours=24)
        ranking_task.start(bot)
    except Exception:
        pass
    try:
        backup_task.change_interval(hours=6)
        backup_task.start(bot)
    except Exception:
        pass


@tasks.loop(minutes=10)
async def rotar_estado(bot: discord.Client):
    mec_activos = 0
    for guild in bot.guilds:
        for miembro in guild.members:
            try:
                if any(role.id in ROLES_TUNEO for role in miembro.roles):
                    mec_activos += 1
            except Exception:
                continue
    estado = next(ESTADOS)
    nombre_estado = getattr(estado, "name", None) or getattr(estado, "type", "Mecánicos")
    try:
        await bot.change_presence(activity=discord.Game(f"{nombre_estado} | Mecánicos activos: {mec_activos}"))
    except Exception:
        await bot.change_presence(activity=discord.Game(f"Mecánicos activos: {mec_activos}"))


@tasks.loop(hours=1)
async def avisar_miembros_identificacion_task(bot: discord.Client):
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
                    f"¡Hola {miembro.display_name}! Para poder ejercer como mecánico, por favor identifícate en el canal correspondiente pulsando el botón y rellenando el formulario. "
                    "Si ya lo hiciste, puedes ignorar este mensaje."
                )
                avisados_identificacion.add(miembro.id)
            except Exception:
                pass


@tasks.loop(minutes=10)
async def keep_alive_task(bot: discord.Client):
    canal = safe_get_channel(bot, CANAL_KEEPALIVE)
    if canal:
        try:
            await canal.send("💤 Ping para mantener activo el bot.", delete_after=2)
        except Exception:
            pass


@tasks.loop(hours=24)
async def ranking_task(bot: discord.Client):
    ahora = datetime.now(ZONA)
    canal = safe_get_channel(bot, CANAL_RANKING)
    if canal is None:
        return
    try:
        if ahora.weekday() == 6:
            ranking = sorted(historial_tuneos.items(), key=lambda x: x[1]["tuneos"], reverse=True)[:5]
            if ranking:
                msg = "🏆 **Ranking semanal de mecánicos:**\n"
                for i, (uid, datos) in enumerate(ranking, 1):
                    user = canal.guild.get_member(uid)
                    nombre = user.display_name if user else f"ID:{uid}"
                    msg += f"{i}️⃣ {nombre} - {datos['tuneos']} tuneos\n"
                await canal.send(msg)
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


@tasks.loop(hours=6)
async def backup_task(bot: discord.Client):
    ok, msg = save_backup()
    if not ok:
        # Optional: log to a channel if desired
        pass
