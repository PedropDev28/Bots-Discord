import os
import json
from typing import Tuple
from datetime import datetime

from config.settings import ZONA
from utils.helpers import historial_tuneos, turnos_activos, tuneos_activos


BACKUP_PATH = os.path.join(os.path.dirname(__file__), "..", "backup.json")
BACKUP_PATH = os.path.abspath(BACKUP_PATH)


def make_backup_dict():
    return {
        "historial_tuneos": historial_tuneos,
        "turnos_activos": turnos_activos,
        "tuneos_activos": tuneos_activos,
    }


def save_backup() -> Tuple[bool, str]:
    try:
        with open(BACKUP_PATH, "w") as f:
            json.dump(make_backup_dict(), f, default=str)
        return True, "OK"
    except Exception as e:
        return False, str(e)


def load_backup() -> Tuple[bool, str]:
    global historial_tuneos, turnos_activos, tuneos_activos
    try:
        if not os.path.exists(BACKUP_PATH):
            return False, "No existe backup.json"
        with open(BACKUP_PATH, "r") as f:
            data = json.load(f)
        historial_tuneos.clear()
        historial_tuneos.update(data.get("historial_tuneos", {}))
        turnos_activos.clear()
        turnos_activos.update(data.get("turnos_activos", {}))
        tuneos_activos.clear()
        tuneos_activos.update(data.get("tuneos_activos", {}))
        return True, "OK"
    except Exception as e:
        return False, str(e)
