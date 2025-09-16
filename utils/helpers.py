import discord
from typing import Optional
from config.constants import CANAL_ANUNCIOS

# Estado runtime (in-memory)
turnos_activos = {}      # user_id -> {"dinero": int, "inicio": datetime}
tuneos_activos = {}      # user_id -> {"dinero": int}
historial_tuneos = {}    # user_id -> {"dinero_total": int, "tuneos": int, "detalle": list}
avisados_identificacion = set()


def has_any_role_by_id(member: discord.Member, role_ids: list) -> bool:
    try:
        return any(role.id in role_ids for role in member.roles)
    except Exception:
        return False


def safe_get_channel(bot: discord.Client, channel_id: int):
    if not channel_id:
        return None
    return bot.get_channel(channel_id)


async def safe_send_interaction(interaction: discord.Interaction, content: str, *, ephemeral: bool = True):
    try:
        if not interaction.response.is_done:
            await interaction.response.send_message(content, ephemeral=ephemeral)
            return None
        try:
            msg = await interaction.followup.send(content, ephemeral=ephemeral)
            return msg
        except discord.NotFound:
            pass
        except Exception:
            pass
        try:
            if interaction.channel:
                msg = await interaction.channel.send(content)
                return msg
        except Exception:
            pass
        try:
            msg = await interaction.user.send(content)
            return msg
        except Exception:
            pass
    except Exception:
        try:
            msg = await interaction.user.send(content)
            return msg
        except Exception:
            return None
    return None


async def enviar_anuncio(bot: discord.Client):
    canal = safe_get_channel(bot, CANAL_ANUNCIOS)
    if canal is None:
        return
    embed = discord.Embed(
        title="📢 ANUNCIO IMPORTANTE – MECÁNICOS OVERSPEED 🔧🚗💨",
        description=(
            "Nuestro bot ya está operativo para gestionar **turnos y tuneos**.\n\n"
            "✅ **Todo se maneja con botones, no con comandos.**"
        ),
        color=discord.Color.orange(),
    )
    embed.add_field(
        name="📝 Identificación",
        value="Consulta el canal de identificación y pulsa el botón para identificarte como Mecánico.",
        inline=False,
    )
    embed.set_footer(text="🔧 Overspeed RP | Taller Oficial")
    try:
        await canal.send(embed=embed)
    except Exception:
        pass
