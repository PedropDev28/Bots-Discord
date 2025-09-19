import io
import discord
import matplotlib.pyplot as plt
from discord.ext import commands
import logging

from config.constants import (
    ROLES_HISTORIAL_TOTAL,
    ROLES_APODOS,
    ROL_PROPIETARIO,
    CANAL_LOGS,
)
from utils.helpers import turnos_activos, tuneos_activos, safe_get_channel, normalize_user_identity
from utils.database import save_backup, load_backup
from utils.supabase_service import supabase_service

logger = logging.getLogger(__name__)

def register_commands(bot: commands.Bot):
    @bot.command(name="help")
    async def help_cmd(ctx):
        prefix = ctx.prefix or "!"
        is_staff = any(r.id in ROLES_HISTORIAL_TOTAL for r in ctx.author.roles)
        fields = []

        # Público
        fields.append((
            "Público",
            "\n".join([
                f"`{prefix}identificar` — Verifica si ya estás identificado.",
            ])
        ))

        # Staff
        if is_staff:
            fields.append((
                "Staff",
                "\n".join([
                    f"`{prefix}historial` — Muestra el historial completo de tuneos.",
                    f"`{prefix}borrar <n>` — Borra los últimos n mensajes del canal.",
                    f"`{prefix}despedir @usuario [razón]` — Expulsa a un usuario con razón.",
                    f"`{prefix}anunciar [canal_id] | Título | Descripción` — Envía un anuncio embed.",
                    f"`{prefix}dashboard` — Muestra el top de actividad (gráfico).",
                    f"`{prefix}guardar` — Guarda el backup actual.",
                    f"`{prefix}cargar` — Carga el backup desde archivo.",
                    f"`{prefix}test_supabase` — Prueba la conexión con Supabase. (admin)",
                    f"`{prefix}migrate_backup` — Migra backup.json a Supabase. (admin)"
                ])
            ))

        # Propietario (rol especial, muestra comando si el autor lo tiene)
        if ROL_PROPIETARIO in [r.id for r in ctx.author.roles]:
            fields.append((
                "Propietario",
                "\n".join([
                    f"`{prefix}cambiarrol @usuario <id_rol>` — Cambia rol y prefijo en apodo.",
                ])
            ))

        embed = discord.Embed(title="Ayuda del bot", color=discord.Color.blurple())
        embed.set_footer(text="Usa los botones en los canales para turnos y tuneos. Los comandos son complementarios.")
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)
        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
    async def historial(ctx):
        if ctx.guild is None:
            await ctx.send("❌ Este comando solo puede ejecutarse en un servidor.")
            return

        # Traer todos los usuarios del servidor (limite alto para simular "todos")
        users = await supabase_service.get_leaderboard(str(ctx.guild.id), limit=1000)
        if not users:
            embed = discord.Embed(
                title="📋 Historial de tuneos",
                description="No hay tuneos registrados.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        lines = []
        for u in users:
            uid = u.get("user_id")
            tuneos = u.get("tuneos_count", 0)
            try:
                uid_int = int(uid)
            except Exception:
                uid_int = uid
            miembro = ctx.guild.get_member(uid_int) if ctx.guild else None
            if miembro:
                apodo = miembro.display_name
            else:
                rol = u.get("rol", "")
                nombre = u.get("nombre", "")
                if rol and nombre:
                    apodo = f"{rol} | {nombre}"
                elif nombre:
                    apodo = nombre
                else:
                    apodo = str(uid)
            lines.append(f"{apodo} | {uid}: {tuneos} tuneos")

        embed = discord.Embed(
            title="📋 Historial completo de tuneos",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
    async def borrar(ctx, cantidad: int):
        deleted = await ctx.channel.purge(limit=cantidad + 1)
        embed = discord.Embed(
            title="🧹 Mensajes borrados",
            description=f"Se borraron {len(deleted)-1 if len(deleted)>0 else 0} mensajes.",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed, delete_after=5)

    @bot.command()
    async def cambiarrol(ctx, miembro: discord.Member, id_rol: int):
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
                canal_logs = safe_get_channel(bot, CANAL_LOGS)
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
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        try:
            await miembro.kick(reason=razon)
            embed = discord.Embed(
                title="🚫 Usuario despedido",
                description=f"{miembro.mention} ha sido despedido del servidor.\nMotivo: {razon}",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            canal_logs = safe_get_channel(bot, CANAL_LOGS)
            if canal_logs:
                embed_log = discord.Embed(
                    title="🚫 Despido registrado",
                    description=f"{miembro.mention} fue despedido por {ctx.author.mention}.\nMotivo: {razon}",
                    color=discord.Color.red(),
                )
                await canal_logs.send(embed=embed_log)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error al despedir",
                description=f"No se pudo despedir a {miembro.mention}. Error: {e}",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            canal_logs = safe_get_channel(bot, CANAL_LOGS)
            if canal_logs:
                embed_log = discord.Embed(
                    title="❌ Error al despedir",
                    description=f"Error al despedir a {miembro.mention} por {ctx.author.mention}: {e}",
                    color=discord.Color.red(),
                )
                await canal_logs.send(embed=embed_log)

    @bot.command(name="anunciar")
    @commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
    async def anunciar(ctx, *, args: str):
        parts = [p.strip() for p in args.split('|', 2)]
        if len(parts) < 2:
            return await ctx.send(
                "Uso: `!anunciar [canal_id] | Titulo | Descripción`  (si no pones canal_id, se usa el canal por defecto)."
            )

        from config.constants import CANAL_ANUNCIOS

        if parts[0].isdigit() and len(parts) > 1 and len(parts[0]) > 5:
            try:
                canal_id = int(parts[0])
            except Exception:
                return await ctx.send("ID de canal inválido.")
            if len(parts) < 3:
                return await ctx.send("Si especificas canal_id, usa: canal_id | Titulo | Descripción")
            title = parts[1]
            description = parts[2]
            canal = bot.get_channel(canal_id)
            if canal is None:
                return await ctx.send("No encuentro ese canal. Asegúrate de que el ID está correcto y que el bot puede ver el canal.")
        else:
            canal = bot.get_channel(CANAL_ANUNCIOS)
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

    @bot.command()
    @commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
    async def dashboard(ctx):
        if ctx.guild is None:
            await ctx.send("❌ Este comando solo puede ejecutarse en un servidor.")
            return

        TOP_N = 10
        users = await supabase_service.get_leaderboard(str(ctx.guild.id), limit=TOP_N)
        if not users:
            embed = discord.Embed(
                title="Sin datos",
                description="No hay datos de tuneos registrados.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        nombres = []
        datos = []
        for u in users:
            uid = u.get("user_id")
            try:
                uid_int = int(uid)
            except Exception:
                uid_int = uid
            miembro = ctx.guild.get_member(uid_int) if ctx.guild else None
            if miembro:
                nombre = miembro.display_name
            else:
                nombre = u.get('nombre') or str(uid)
            nombres.append(nombre)
            datos.append(u.get('tuneos_count', 0))

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
        cmap = plt.get_cmap('viridis')
        colors = [cmap(i / max(1, len(nombres)-1)) for i in range(len(nombres))]

        ax.barh(y_pos, datos, color=colors)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(nombres)
        ax.invert_yaxis()
        ax.set_xlabel('Tuneos')
        ax.set_title('Top mecánicos por tuneos')

        for i, v in enumerate(datos):
            ax.text(v + max(1, int(max(datos) * 0.01)), i, str(v), va='center')

        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        plt.close(fig)

        # Total de tuneos calculado a partir de usuarios traídos (si quieres total de todo el servidor, puedes aumentar el limit)
        total_tuneos = sum(u.get('tuneos_count', 0) for u in users)
        top1 = nombres[0] if nombres else 'N/A'
        embed = discord.Embed(
            title="📊 Dashboard de actividad",
            description=f"Total de tuneos registrados: **{total_tuneos}**\nTop 1: **{top1}**",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed, file=discord.File(buf, filename="dashboard.png"))

    @bot.command()
    @commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
    async def guardar(ctx):
        ok, msg = save_backup()
        if ok:
            embed = discord.Embed(
                title="✅ Datos guardados",
                description="Los datos se han guardado correctamente.",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="❌ Error al guardar", description=msg, color=discord.Color.red())
            await ctx.send(embed=embed)

    @bot.command()
    @commands.has_any_role(*ROLES_HISTORIAL_TOTAL)
    async def cargar(ctx):
        ok, msg = load_backup()
        if ok:
            embed = discord.Embed(
                title="✅ Datos cargados",
                description="Los datos se han restaurado correctamente.",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="❌ Error al cargar", description=msg, color=discord.Color.red())
            await ctx.send(embed=embed)

    @bot.command()
    async def identificar(ctx):
        from config.constants import ROLE_APRENDIZ
        aprendiz_rol = ctx.guild.get_role(ROLE_APRENDIZ)
        if aprendiz_rol in ctx.author.roles and ctx.author.display_name.startswith("🧰 APR"):
            embed = discord.Embed(
                title="✅ Ya estás identificado",
                description="Ya tienes el rol de aprendiz y el apodo configurado.",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)
            # asegurar existencia en supabase
            try:
                target_user_id, clean_name = normalize_user_identity(ctx.author.display_name, ctx.author.id)
                await supabase_service.create_or_update_user(
                    user_id=str(target_user_id),
                    nombre=clean_name,
                    rol="🧰 APR",
                    server_id=str(ctx.guild.id)
                )
            except Exception as e:
                logger.exception("Error al asegurar usuario en supabase tras identificar")
            return
