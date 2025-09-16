import os
import traceback
import discord

from config.constants import (
    ROLE_APRENDIZ,
    ROLE_OVERSPEED,
    CANAL_IDENTIFICACION,
    CANAL_RESULTADO_IDENTIFICACION,
    CANAL_LOGS,
    CANAL_STAFF,
)
from config.settings import ZONA
from utils.helpers import safe_get_channel, safe_send_interaction


# Funciones para el nuevo flujo de identificación en canal
async def handle_identification_channel(bot, user, guild, canal_ident):
    """
    Maneja la identificación completa en el canal.
    Retorna (success: bool, error_msg: str)
    """
    try:
        # Verificar si ya está identificado
        rol_aprendiz = guild.get_role(ROLE_APRENDIZ) if guild else None
        if rol_aprendiz and rol_aprendiz in user.roles and user.display_name.startswith("🧰 APR"):
            return False, "Ya estás identificado"

        def check_author_channel(m: discord.Message):
            return m.author.id == user.id and m.channel.id == canal_ident.id

        # Mensaje inicial
        embed_inicio = discord.Embed(
            title="🆔 Proceso de Identificación",
            description=f"Hola {user.mention}! Vamos a completar tu identificación como mecánico.\nEscribe 'cancelar' en cualquier momento para abortar.",
            color=discord.Color.blue()
        )
        msg_inicio = await canal_ident.send(embed=embed_inicio)

        # Pregunta 1: Nombre IC
        try:
            embed_pregunta1 = discord.Embed(
                title="📝 Nombre IC",
                description="¿Cuál es tu Nombre IC? (máximo 32 caracteres)",
                color=discord.Color.orange()
            )
            msg_pregunta1 = await canal_ident.send(embed=embed_pregunta1)
            
            nombre_msg = await bot.wait_for("message", timeout=120, check=check_author_channel)
            nombre = nombre_msg.content.strip()
            
            # Borrar mensaje del usuario
            try:
                await nombre_msg.delete()
            except Exception:
                pass
            
            if nombre.lower() == "cancelar":
                embed_cancel = discord.Embed(
                    title="❌ Operación Cancelada",
                    description="El proceso de identificación ha sido cancelado.",
                    color=discord.Color.red()
                )
                await canal_ident.send(embed=embed_cancel, delete_after=5)
                # Limpiar mensajes del proceso
                try:
                    await msg_inicio.delete()
                    await msg_pregunta1.delete()
                except Exception:
                    pass
                return False, "Operación cancelada"
                
            if len(nombre) == 0 or len(nombre) > 32:
                embed_error = discord.Embed(
                    title="❌ Nombre Inválido",
                    description="El nombre debe tener entre 1 y 32 caracteres. Vuelve a intentarlo con el botón.",
                    color=discord.Color.red()
                )
                await canal_ident.send(embed=embed_error, delete_after=8)
                # Limpiar mensajes del proceso
                try:
                    await msg_inicio.delete()
                    await msg_pregunta1.delete()
                except Exception:
                    pass
                return False, "Nombre inválido"
                
        except Exception:
            embed_timeout = discord.Embed(
                title="⏰ Tiempo Agotado",
                description="No recibí respuesta a tiempo. Vuelve a intentarlo con el botón.",
                color=discord.Color.red()
            )
            await canal_ident.send(embed=embed_timeout, delete_after=8)
            # Limpiar mensajes del proceso
            try:
                await msg_inicio.delete()
                await msg_pregunta1.delete()
            except Exception:
                pass
            return False, "Tiempo agotado"

        # Pregunta 2: ID IC
        try:
            embed_pregunta2 = discord.Embed(
                title="🔢 ID IC",
                description="¿Cuál es tu ID IC? (máximo 10 caracteres, solo números)",
                color=discord.Color.orange()
            )
            msg_pregunta2 = await canal_ident.send(embed=embed_pregunta2)
            
            id_msg = await bot.wait_for("message", timeout=120, check=check_author_channel)
            id_ic = id_msg.content.strip()
            
            # Borrar mensaje del usuario
            try:
                await id_msg.delete()
            except Exception:
                pass
            
            if id_ic.lower() == "cancelar":
                embed_cancel = discord.Embed(
                    title="❌ Operación Cancelada",
                    description="El proceso de identificación ha sido cancelado.",
                    color=discord.Color.red()
                )
                await canal_ident.send(embed=embed_cancel, delete_after=5)
                # Limpiar mensajes del proceso
                try:
                    await msg_inicio.delete()
                    await msg_pregunta1.delete()
                    await msg_pregunta2.delete()
                except Exception:
                    pass
                return False, "Operación cancelada"
                
            if len(id_ic) == 0 or len(id_ic) > 10 or not id_ic.isdigit():
                embed_error = discord.Embed(
                    title="❌ ID Inválido",
                    description="El ID debe tener máximo 10 números. Vuelve a intentarlo con el botón.",
                    color=discord.Color.red()
                )
                await canal_ident.send(embed=embed_error, delete_after=8)
                # Limpiar mensajes del proceso
                try:
                    await msg_inicio.delete()
                    await msg_pregunta1.delete()
                    await msg_pregunta2.delete()
                except Exception:
                    pass
                return False, "ID inválido"
                
        except Exception:
            embed_timeout = discord.Embed(
                title="⏰ Tiempo Agotado",
                description="No recibí respuesta a tiempo. Vuelve a intentarlo con el botón.",
                color=discord.Color.red()
            )
            await canal_ident.send(embed=embed_timeout, delete_after=8)
            # Limpiar mensajes del proceso
            try:
                await msg_inicio.delete()
                await msg_pregunta1.delete()
                await msg_pregunta2.delete()
            except Exception:
                pass
            return False, "Tiempo agotado"

        # Aplicar cambios
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
            embed_error_permisos = discord.Embed(
                title="❌ Sin Permisos",
                description="No tengo permisos para cambiar tu apodo. Contacta con un administrador.",
                color=discord.Color.red()
            )
            await canal_ident.send(embed=embed_error_permisos, delete_after=8)
            if canal_resultado:
                try:
                    await canal_resultado.send(
                        f"❌ Error al identificar a {user.mention}: No tengo permisos para cambiar el apodo."
                    )
                except Exception:
                    pass
            # Limpiar mensajes del proceso
            try:
                await msg_inicio.delete()
                await msg_pregunta1.delete()
                await msg_pregunta2.delete()
            except Exception:
                pass
            return False, "No tengo permisos para cambiar tu apodo"
        except Exception as e:
            embed_error_generico = discord.Embed(
                title="❌ Error Inesperado",
                description="Ocurrió un error al cambiar tu apodo. Contacta con un administrador.",
                color=discord.Color.red()
            )
            await canal_ident.send(embed=embed_error_generico, delete_after=8)
            if canal_resultado:
                try:
                    await canal_resultado.send(
                        f"❌ Error no esperado al identificar a {user.mention} (cambio de apodo): {e}"
                    )
                except Exception:
                    pass
            # Limpiar mensajes del proceso
            try:
                await msg_inicio.delete()
                await msg_pregunta1.delete()
                await msg_pregunta2.delete()
            except Exception:
                pass
            return False, f"Error no esperado: {e}"

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

        # Registrar en hilo del canal de identificación
        try:
            thread_name = "Identificaciones Mecánicos"
            thread = None
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

        # Mensaje de éxito que se borra a los 5 segundos
        embed_exito = discord.Embed(
            title="✅ Identificación Completada",
            description=f"¡Perfecto! Tu apodo ha sido cambiado a: `{nuevo_apodo}`\n\nYa puedes usar los botones de turnos y tuneos.",
            color=discord.Color.green()
        )
        embed_exito.set_footer(text="Este mensaje se eliminará en 5 segundos")
        await canal_ident.send(embed=embed_exito, delete_after=5)

        # Limpiar todos los mensajes del proceso de identificación
        try:
            await msg_inicio.delete()
            await msg_pregunta1.delete()
            await msg_pregunta2.delete()
        except Exception:
            pass

        return True, f"Identificación completada. Apodo cambiado a: {nuevo_apodo}"

    except Exception as e:
        # Log del error
        tb = traceback.format_exc()
        canal_logs = safe_get_channel(bot, CANAL_LOGS)
        if canal_logs:
            try:
                await canal_logs.send(
                    f"❌ Error en handle_identification_dm para <@{user.id}>: {e}\n```{tb[:1900]}```"
                )
            except Exception:
                pass
        
        canal_staff = safe_get_channel(bot, CANAL_STAFF)
        if canal_staff:
            try:
                await canal_staff.send(
                    f"❌ Error no manejado en identificación de {user.mention}: {e}"
                )
            except Exception:
                pass
        
        return False, "Error interno del bot"


# Función legacy del modal (se mantiene por compatibilidad pero no se usa)
class IdentificacionModalLegacy:
    """Modal legacy - ya no se usa, reemplazado por handle_identification_dm"""
    pass
