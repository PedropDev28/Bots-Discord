import os
import traceback
import discord
from discord.ui import Modal, TextInput

from config.constants import (
    ROLE_APRENDIZ,
    ROLE_OVERSPEED,
    CANAL_IDENTIFICACION,
    CANAL_RESULTADO_IDENTIFICACION,
    CANAL_LOGS,
)
from config.settings import ZONA
from utils.helpers import safe_get_channel, safe_send_interaction


class IdentificacionModal(Modal, title="Identificación de mecánico"):
    nombre_ic = TextInput(label="Nombre IC", placeholder="Ej: John Doe", max_length=32)
    id_ic = TextInput(label="ID IC", placeholder="Ej: 12345", max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            try:
                rol_aprendiz = interaction.guild.get_role(ROLE_APRENDIZ) if interaction.guild else None
                if rol_aprendiz and rol_aprendiz in interaction.user.roles and interaction.user.display_name.startswith("🧰 APR"):
                    await safe_send_interaction(interaction, "⚠️ Ya estás identificado.")
                    return
            except Exception:
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
                await safe_send_interaction(interaction, "⚠️ No tengo permisos para cambiar tu apodo.", ephemeral=True)
                if canal_identificacion:
                    try:
                        await canal_identificacion.send(
                            f"❌ Error al identificar a {interaction.user.mention}: No tengo permisos para cambiar el apodo."
                        )
                    except Exception:
                        pass
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

            try:
                canal = interaction.guild.get_channel(CANAL_IDENTIFICACION)
                thread_name = "Identificaciones Mecánicos"
                thread = None
                if canal:
                    # Intentar encontrar un thread existente con el mismo nombre
                    for th in canal.threads:
                        if th.name == thread_name:
                            thread = th
                            break
                    if thread is None:
                        try:
                            thread = await canal.create_thread(
                                name=thread_name,
                                type=discord.ChannelType.private_thread,
                                invitable=False,
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
                pass

            await safe_send_interaction(interaction, f"✅ Identificación completada. Apodo cambiado a: {nuevo_apodo}", ephemeral=True)
        except Exception as e:
            tb = traceback.format_exc()
            canal_logs = safe_get_channel(interaction.client, CANAL_LOGS)
            if canal_logs:
                try:
                    await canal_logs.send(
                        f"❌ Error en IdentificacionModal.on_submit para <@{interaction.user.id}>: {e}\n```{tb[:1900]}```"
                    )
                except Exception:
                    pass
            try:
                log_path = os.path.join(os.path.dirname(__file__), "..", "ident_errors.log")
                with open(os.path.abspath(log_path), "a") as lf:
                    lf.write(
                        f"[{ZONA.localize(__import__('datetime').datetime.now()).isoformat()}] Error en IdentificacionModal.on_submit para {interaction.user.id}: {e}\n{tb}\n---\n"
                    )
            except Exception:
                pass
            try:
                await safe_send_interaction(
                    interaction,
                    "❌ Algo salió mal, inténtalo de nuevo. Si el problema persiste, contacta con un administrador.",
                    ephemeral=True,
                )
            except Exception:
                pass
