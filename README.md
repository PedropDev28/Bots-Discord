# Bots-Discord

Estructura modular del bot de Discord para Overspeed RP.

## Estructura

- main.py
- config/
  - settings.py
  - constants.py
- utils/
  - helpers.py
  - database.py
- handlers/
  - identification.py
  - commands.py
- tasks/
  - periodic.py
- views/
  - ui_components.py

## Ejecutar

1. Configura la variable de entorno `DISCORD_TOKEN` con el token del bot.
2. Instala dependencias de `requirements.txt`.
3. Ejecuta:

```
python main.py
```

## Notas

- Los IDs de roles y canales están en `config/constants.py`.
- Los datos en memoria (turnos, tuneos, historial) se guardan/cargan con `!guardar` y `!cargar` en `backup.json`.
