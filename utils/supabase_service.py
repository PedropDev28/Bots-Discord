from typing import List, Dict, Optional, Any
from datetime import datetime
import os
import json
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        # Railway automáticamente carga las variables de entorno
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_ANON_KEY")
        self.client: Optional[Client] = None
        
        if not self.url or not self.key:
            logger.error("Supabase credentials not found in environment variables")
            raise ValueError("Missing Supabase configuration")
    
    def get_client(self) -> Client:
        """Obtiene el cliente de Supabase"""
        if not self.client:
            try:
                self.client = create_client(self.url, self.key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise
        return self.client
    
    async def test_connection(self) -> bool:
        """Prueba la conexión con Supabase"""
        try:
            client = self.get_client()
            # Intentar hacer una consulta simple
            result = client.table("users").select("count", count="exact").limit(1).execute()
            logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            logger.error(f"Supabase connection test failed: {e}")
            return False
    
    async def create_or_update_user(self, user_id: str, nombre: str, rol: str, server_id: str) -> bool:
        """Crea o actualiza un usuario"""
        try:
            client = self.get_client()
            
            data = {
                "user_id": user_id,
                "nombre": nombre,
                "rol": rol,
                "server_id": server_id,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Usar upsert para crear o actualizar
            result = client.table("users").upsert(data).execute()
            logger.info(f"User {user_id} created/updated")
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error creating/updating user {user_id}: {e}")
            return False
    
    async def get_user_stats(self, user_id: str, server_id: str) -> Optional[Dict]:
        """Obtiene las estadísticas de un usuario"""
        try:
            client = self.get_client()
            result = client.table("users").select("*").eq("user_id", user_id).eq("server_id", server_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {e}")
            return None
    
    async def get_leaderboard(self, server_id: str, limit: int = 10) -> List[Dict]:
        """Obtiene el ranking de usuarios por tuneos"""
        try:
            client = self.get_client()
            result = client.table("users").select("*").eq("server_id", server_id).order("tuneos_count", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    async def increment_tuneo_count(self, user_id: str, server_id: str) -> bool:
        """Incrementa el contador de tuneos de un usuario"""
        try:
            client = self.get_client()
            
            # Obtener el usuario actual
            user = await self.get_user_stats(user_id, server_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            # Incrementar el contador
            new_count = user.get('tuneos_count', 0) + 1
            
            result = client.table("users").update({
                "tuneos_count": new_count,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).eq("server_id", server_id).execute()
            
            logger.info(f"Tuneo count incremented for user {user_id}: {new_count}")
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error incrementing tuneo count for {user_id}: {e}")
            return False
    
    async def migrate_from_backup(self, backup_data: dict, server_id: str) -> bool:
        """Migra datos desde el backup.json - solo nombre, rol y cantidad de tuneos"""
        try:
            historial = backup_data.get("historial_tuneos", {})
            migrated_count = 0
            
            client = self.get_client()
            
            for user_id, user_data in historial.items():
                try:
                    # Solo crear el usuario con los datos básicos
                    user_record = {
                        "user_id": user_id,
                        "nombre": user_data["nombre"],
                        "rol": user_data["rol"],
                        "tuneos_count": user_data["tuneos"],
                        "server_id": server_id,
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                    
                    result = client.table("users").upsert(user_record).execute()
                    
                    if result.data:
                        migrated_count += 1
                        logger.info(f"Migrated: {user_data['nombre']} - {user_data['tuneos']} tuneos")
                
                except Exception as e:
                    logger.error(f"Error migrating user {user_id}: {e}")
                    continue
        
            logger.info(f"Migration completed: {migrated_count} users migrated")
            return True
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            return False

# Instancia singleton
supabase_service = SupabaseService()