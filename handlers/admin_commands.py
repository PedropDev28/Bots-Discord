import discord
from discord.ext import commands
from utils.supabase_service import supabase_service
import json
import os
import logging

logger = logging.getLogger(__name__)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="test_supabase")
    @commands.has_permissions(administrator=True)
    async def test_supabase(self, ctx: commands.Context):
        """Prueba la conexión con Supabase"""
        await ctx.send("🔄 Probando conexión con Supabase...")
        
        success = await supabase_service.test_connection()
        
        if success:
            await ctx.send("✅ Conexión con Supabase exitosa!")
        else:
            await ctx.send("❌ Error de conexión con Supabase. Revisa los logs.")
    
    @commands.command(name="migrate_backup")
    @commands.has_permissions(administrator=True)
    async def migrate_backup(self, ctx: commands.Context):
        """Migra los datos del backup.json a Supabase"""
        if ctx.guild is None:
            await ctx.send("❌ Este comando solo puede ejecutarse en un servidor.")
            return

        await ctx.send("🔄 Iniciando migración de datos...")
        
        try:
            # Ruta al backup.json en la raíz del proyecto
            backup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backup.json")
            backup_path = os.path.abspath(backup_path)
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            success = await supabase_service.migrate_from_backup(backup_data, str(ctx.guild.id))
            
            if success:
                await ctx.send("✅ Migración completada exitosamente!")
            else:
                await ctx.send("❌ Error durante la migración. Revisa los logs.")
                
        except FileNotFoundError:
            logger.exception("backup.json no encontrado")
            await ctx.send("❌ Archivo backup.json no encontrado.")
        except Exception as e:
            logger.exception("Error durante migrate_backup")
            await ctx.send(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))