import os
import json
import logging
from typing import Tuple
from datetime import datetime

from config.settings import ZONA
from utils.helpers import historial_tuneos, turnos_activos, tuneos_activos
from utils.supabase_service import supabase_service

logger = logging.getLogger(__name__)

BACKUP_PATH = os.path.join(os.path.dirname(__file__), "..", "backup.json")
BACKUP_PATH = os.path.abspath(BACKUP_PATH)


def make_backup_dict():
    """
    Construye el dict de backup. Si hay Supabase configurado, intenta leer
    la tabla `users` y usar esos datos para `historial_tuneos`. En cualquier
    caso incluye las estructuras en memoria de turnos/tuneos activos.
    """
    historial = {}
    try:
        client = supabase_service.get_client()
        res = client.table("users").select("*").execute()
        rows = res.data or []
        for r in rows:
            uid = str(r.get("user_id"))
            historial[uid] = {
                "nombre": r.get("nombre") or "",
                "rol": r.get("rol") or "",
                "tuneos": int(r.get("tuneos_count", 0) or 0),
            }
    except Exception:
        # Si falla la consulta a Supabase, usar el historial en memoria
        historial = dict(historial_tuneos)

    return {
        "historial_tuneos": historial,
        "turnos_activos": dict(turnos_activos),
        "tuneos_activos": dict(tuneos_activos),
        "exported_at": datetime.utcnow().isoformat()
    }


def save_backup() -> Tuple[bool, str]:
    """
    Guarda backup.json en disco. Intenta exportar desde Supabase si está disponible,
    sino utiliza las estructuras en memoria.
    """
    try:
        payload = make_backup_dict()
        with open(BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        return True, "OK"
    except Exception as e:
        logger.exception("Error guardando backup")
        return False, str(e)


def load_backup() -> Tuple[bool, str]:
    """
    Carga backup.json en memoria y, si Supabase está disponible, sincroniza la tabla `users`
    con los datos básicos (user_id, nombre, rol, tuneos_count, server_id si existe).
    """
    global historial_tuneos, turnos_activos, tuneos_activos
    try:
        if not os.path.exists(BACKUP_PATH):
            return False, "No existe backup.json"
        with open(BACKUP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Actualizar estructuras en memoria
        historial_tuneos.clear()
        historial_tuneos.update(data.get("historial_tuneos", {}))
        turnos_activos.clear()
        turnos_activos.update(data.get("turnos_activos", {}))
        tuneos_activos.clear()
        tuneos_activos.update(data.get("tuneos_activos", {}))

        # Si Supabase está disponible, sincronizar usuarios (upsert)
        try:
            client = supabase_service.get_client()
            migrated = 0
            for user_id, u in historial_tuneos.items():
                try:
                    user_record = {
                        "user_id": str(user_id),
                        "nombre": u.get("nombre", ""),
                        "rol": u.get("rol", ""),
                        "tuneos_count": int(u.get("tuneos", 0) or 0),
                        # NO seteamos server_id por defecto aquí, dejar al caller o comandos de migración
                    }
                    client.table("users").upsert(user_record).execute()
                    migrated += 1
                except Exception:
                    logger.exception("Error upsert user %s", user_id)
                    continue
            logger.info("Loaded backup and upserted %d users to Supabase", migrated)
        except Exception:
            # Si no hay supabase o falla, simplemente continuar (datos en memoria ya cargados)
            logger.info("Supabase no disponible o falló sincronización. Datos cargados en memoria.")

        return True, "OK"
    except Exception as e:
        logger.exception("Error cargando backup")
        return False, str(e)
