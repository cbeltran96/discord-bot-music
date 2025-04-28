# Discord Music Bot

Un bot de Discord en Python para reproducir música desde YouTube y Spotify, con control por reacciones y manejo de playlists de forma eficiente.

---

## 🔥 Características

- 🎵 **Reproducción desde YouTube** (videos individuales o playlists).
- 🎧 **Integración con Spotify**: convierte playlists/tracks de Spotify en streams de YouTube.
- ⏯️ **Control por reacciones**: pausa, reanuda, salta y detiene con emojis.
- 📋 **Colas dinámicas**: reproducción inmediata de la primera pista y carga paulatina del resto.
- 🔍 **Búsqueda inteligente**: normalización y filtros para emparejar mejor los títulos.
- 🐍 **Implementado en Python** con `discord.py` y `yt-dlp`.

---

## 🚀 Instalación

1. **Clona el repositorio**:
   ```bash
   git clone https://github.com/tu-usuario/discord-music-bot.git
   cd discord-music-bot
   ```

2. **Crea un entorno virtual** (recomendado):
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\\Scripts\\activate  # Windows
   ```

3. **Instala dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Variables de entorno**: crea un archivo `.env` en la raíz con:
   ```ini
   DISCORD_TOKEN=tu_token_de_discord
   SPOTIFY_CLIENT_ID=tu_client_id_spotify
   SPOTIFY_CLIENT_SECRET=tu_client_secret_spotify
   ```

5. **Configura `ffmpeg`** en tu sistema y asegúrate de que esté en el PATH.

---

## 🛠️ Uso

1. **Inicia el bot**:
   ```bash
   python bot.py
   ```

2. **Invita el bot a tu servidor** usando su OAuth2 con permisos de `VOICE` y `MESSAGE_CONTENT`.

3. **Comandos principales**:
   - `.unir` — Conecta el bot a tu canal de voz.
   - `.reproducir <URL>` o `.p <URL>` — Reproduce un track o playlist de YouTube/Spotify.
   - `.pausar` / `.reanudar` — Pausa y retoma la reproducción.
   - `.saltar` / `.skip` — Salta la pista actual.
   - `.detener` / `.stop` — Detiene la reproducción y desconecta.

4. **Controles por reacciones** (aparecen tras `Reproduciendo…`):
   - ⏯️ Pausa/Resume
   - ⏭️ Skip
   - ⏹️ Stop + desconexión

---

## ⚙️ Flujo de Reproducción

Cuando pasas una **playlist**:
1. Extrae las pistas con `yt-dlp` o Spotify API.
2. **Reproduce inmediatamente** la primera pista.
3. **Encola** el resto de forma asíncrona con pausas, sin bloquear.
4. Al terminar cada pista, el callback `after_play` arranca la siguiente de la cola.
5. Al completar el encolado, el bot envía un **solo mensaje** en Markdown con la lista de títulos que van en cola.

---

## 📂 Estructura del Proyecto

```
├── bot.py           # Código principal del bot
├── requirements.txt # Dependencias de Python
├── .env             # Variables de entorno (no versionar)
└── README.md        # Este archivo
```

---

## 📚 Dependencias

- `discord.py`
- `yt-dlp`
- `spotipy`
- `python-dotenv`
- `unidecode`

Instaladas via:
```bash
pip install discord.py yt-dlp spotipy python-dotenv unidecode
```

---

## 🤝 Contribuciones

¡Bienvenidas! Por favor abre un _issue_ para discutir cambios grandes o haz un _pull request_.