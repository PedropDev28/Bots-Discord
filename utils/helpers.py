import discord
import re
from typing import Tuple, Optional
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

    PROMO_THRESHOLD = 20
    PROMO_NOTIFY_CHANNEL_ID = 1385301437977854046

    embed = discord.Embed(
        title="📢 ANUNCIO IMPORTANTE – MECÁNICOS OVERSPEED 🔧🚗💨",
        description=(
            "Nuestro bot ya está operativo para gestionar **turnos y tuneos**.\n\n"
            "✅ **Todo se maneja con botones, no con comandos.**\n\n"
            "Pulsa el botón de identificación para registrarte como mecánico y usa los botones de "
            "turnos/tuneos para gestionar tu actividad."
        ),
        color=discord.Color.orange(),
    )
    embed.add_field(
        name="📝 Identificación",
        value="Pulsa el botón en el canal de identificación para completar tu ficha de mecánico.",
        inline=False,
    )
    embed.add_field(
        name="⏱️ Turnos y 🔧 Tuneos",
        value="Inicia y finaliza turnos con los botones. Añade tuneos usando los botones de precios y finalízalos cuando termines.",
        inline=False,
    )
    embed.add_field(
        name="📈 Promociones automáticas (info para todos)",
        value=(
            f"Cuando un mecánico supera los {PROMO_THRESHOLD} tuneos, el sistema lo marcará para revisión.\n"
            f"Las notificaciones de subida/degradación de rango se publican en el canal <#{PROMO_NOTIFY_CHANNEL_ID}> "
            "para que el staff revise los ascensos."
        ),
        inline=False,
    )
    embed.set_footer(text="🔧 Overspeed RP | Taller Oficial — Usa los botones en los canales correspondientes.")
    try:
        await canal.send(embed=embed)
    except Exception:
        try:
            # Fallback: enviar texto simple si embed falla
            await canal.send(
                "El bot está activo para gestionar turnos y tuneos. Pulsa el botón de identificación en el canal correspondiente. "
                f"Promociones automáticas al superar {PROMO_THRESHOLD} tuneos (notificaciones en <#{PROMO_NOTIFY_CHANNEL_ID}>)."
            )
        except Exception:
            pass


def extract_legacy_id(display_name: str) -> Optional[str]:
    """Extrae un posible ID legacy al final del apodo '... | 11895'"""
    if not display_name:
        return None
    m = re.search(r'\b(\d{3,12})\s*$', display_name)
    return m.group(1) if m else None


def clean_display_name(display_name: str) -> str:
    """Limpia el display_name quitando prefijos/apodos y el ID final si existe.
    Ejemplos:
      '🏢PROP | Gencho | 11895' -> 'Gencho'
      '🧰 APR | Nombre | 123' -> 'Nombre'
      'Usuario' -> 'Usuario'
    """
    if not display_name:
        return ""
    parts = [p.strip() for p in display_name.split('|')]
    # si último fragmento es numérico, eliminarlo
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    # si quedan 2+ partes, el nombre suele estar en la segunda parte
    if len(parts) >= 2:
        return parts[1]
    # si sólo hay una parte, devolverla tal cual (sin emojis al inicio)
    return parts[0].strip()


def normalize_user_identity(display_name: str, discord_id: int) -> Tuple[str, str]:
    """
    Retorna (target_user_id, clean_name)
      - target_user_id: legacy id si existe en el display_name, sino discord_id as str
      - clean_name: nombre limpio para guardar en la BD
    """
    legacy = extract_legacy_id(display_name)
    target = legacy or str(discord_id)
    clean = clean_display_name(display_name)
    # si clean vació, usar discord_id como fallback
    if not clean:
        clean = str(discord_id)
    return target, clean
