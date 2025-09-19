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
            
            # Verificar si el usuario existe
            existing = client.table("users").select("*").eq("user_id", user_id).eq("server_id", server_id).execute()
            
            data = {
                "user_id": user_id,
                "nombre": nombre,
                "rol": rol,
                "server_id": server_id,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if existing.data:
                # Actualizar usuario existente
                result = client.table("users").update(data).eq("user_id", user_id).eq("server_id", server_id).execute()
                logger.info(f"User {user_id} updated")
            else:
                # Crear nuevo usuario
                data["created_at"] = datetime.utcnow().isoformat()
                result = client.table("users").insert(data).execute()
                logger.info(f"User {user_id} created")
            
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
    
    async def add_tuneo(self, user_id: str, server_id: str, car_name: str = None) -> bool:
        """Añade un tuneo completado"""
        try:
            client = self.get_client()
            data = {
                "user_id": user_id,
                "server_id": server_id,
                "car_name": car_name or "Vehículo no especificado",
                "tuning_data": {},
                "status": "completado",
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = client.table("tuneos").insert(data).execute()
            logger.info(f"Tuneo added for user {user_id}")
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error adding tuneo for {user_id}: {e}")
            return False
    
    async def migrate_from_backup(self, backup_data: dict, server_id: str) -> bool:
        """Migra datos desde el backup.json (para usar en Railway)"""
        try:
            historial = backup_data.get("historial_tuneos", {})
            migrated_count = 0
            
            for user_id, user_data in historial.items():
                # Crear/actualizar usuario
                success = await self.create_or_update_user(
                    user_id=user_id,
                    nombre=user_data["nombre"],
                    rol=user_data["rol"],
                    server_id=server_id
                )
                
                if success:
                    # Crear registros de tuneos históricos
                    tuneos_count = user_data.get("tuneos", 0)
                    for i in range(tuneos_count):
                        await self.add_tuneo(
                            user_id=user_id,
                            server_id=server_id,
                            car_name=f"Tuneo histórico #{i + 1}"
                        )
                    migrated_count += 1
                    logger.info(f"Migrated user {user_data['nombre']} with {tuneos_count} tuneos")
            
            logger.info(f"Migration completed: {migrated_count} users migrated")
            return True
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            return False

# Instancia singleton
supabase_service = SupabaseService()