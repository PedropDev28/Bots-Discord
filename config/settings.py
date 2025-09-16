import discord
import pytz

# Intents y prefijo del bot
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.members = True

PREFIX = "!"

# Zona horaria
ZONA = pytz.timezone("Europe/Madrid")
