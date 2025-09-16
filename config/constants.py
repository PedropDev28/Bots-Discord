import discord
import itertools

# Precios de los tuneos
PRECIOS_TUNEOS = {
    "Frenos": 80000,
    "Motor": 80000,
    "Suspensión": 80000,
    "Transmisión": 80000,
    "Blindaje": 105000,
    "Turbo": 100000,
    "Full tuning con blindaje": 525000,
    "Full tuning sin blindaje": 450000,
    "Cambio estético": 20000,
    "Reparación en el taller": 10000,
    "Reparación en la calle": 15000,
    "Kit de reparación": 50000,
}

# Roles
ROLES_TUNEO = [
    1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425,
    1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423,
    1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882,
    1391019755267424347, 1385301435456950391, 1385301435456950390, 1415954460202766386,
]

ROLES_HISTORIAL_TOTAL = [
    1385301435499151429, 1385301435499151427, 1385301435499151426, 1385301435499151425,
    1387806963001331743, 1387050926476365965, 1410548111788740620, 1385301435499151423,
    1385301435499151422, 1385301435456950394, 1391019848414400583, 1391019868630945882,
    1415954460202766386,
]

ROL_PROPIETARIO = 1410548111788740620
ROL_MIEMBRO = 1387524774485299391

ROLES_APODOS = {
    1385301435456950391: ("🔧 MEC", "MEC"),
    1391019848414400583: ("⭐ GER", "GER"),
    1385301435499151423: ("⭐ JEF", "JEF"),
    1391019868630945882: ("⭐ SUBGER", "SUBGER"),
    1385301435499151422: ("⭐ SUBJEF", "SUBJEF"),
    1385301435456950394: ("👑 GER. GEN.", "GER. GEN."),
    1391019755267424347: ("📋 REC", "REC"),
    1385301435456950390: ("🧰 APR", "APR"),
}

# Canales
CANAL_IDENTIFICACION = 1416880543122849802
ROLE_APRENDIZ = 1385301435456950390
ROLE_OVERSPEED = 1387571297705394250
CANAL_TURNOS = 1415949790545711236
CANAL_TUNEOS = 1415963375485321226
CANAL_RANKING = 1416021337519947858
CANAL_KEEPALIVE = 1387055864866799637
CANAL_ANUNCIOS = 1387551821224214839
CANAL_RESULTADO_IDENTIFICACION = 1417250457163665418
CANAL_STAFF = 1415964136550043689
CANAL_LOGS = 1417250932386959441

# Estados rotativos del bot
ESTADOS = itertools.cycle([
    discord.Game("Gestionando turnos ⏱️"),
    discord.Activity(type=discord.ActivityType.listening, name="a los reportes 📋"),
    discord.Activity(type=discord.ActivityType.watching, name="los tuneos en curso 🔧"),
    discord.Activity(type=discord.ActivityType.competing, name="por ser el mejor mecánico 💰"),
    discord.Game("tunear hasta el fin 🚗💨"),
    discord.Activity(type=discord.ActivityType.listening, name="los escapes sonar 🔊"),
    discord.Activity(type=discord.ActivityType.watching, name="el humo del taller 🚬"),
    discord.Activity(type=discord.ActivityType.competing, name="con Fast & Furious 🏎️🔥"),
    discord.Game("con aceite y gasolina ⛽"),
    discord.Activity(type=discord.ActivityType.watching, name="a los clientes esperar 😅"),
])
