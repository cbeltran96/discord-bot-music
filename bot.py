import discord
from discord.ext import commands
import asyncio
import yt_dlp
from dotenv import load_dotenv, find_dotenv
import os, pathlib, re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# ─── CARGA DE CONFIGURACIÓN ─────────────────────────────────────────────────
load_dotenv(find_dotenv())
TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# ─── SETUP DE SPOTIFY ─────────────────────────────────────────────────────────
SPOT_TRACK = re.compile(r"(?:https?://open\.spotify\.com/track/|spotify:track:)([A-Za-z0-9]+)")
SPOT_PLAYLIST = re.compile(r"(?:https?://open\.spotify\.com/playlist/|spotify:playlist:)([A-Za-z0-9]+)")
_spotify = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    auth = SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
    _spotify = spotipy.Spotify(client_credentials_manager=auth)

# ─── CONFIGURACIÓN DE YTDL (yt-dlp) ──────────────────────────────────────────
COOKIE_FILE = pathlib.Path("youtube_cookies.txt")
ytdl_opts = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "http_headers": {
        # cabezera de un Android moderno
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13; Pixel 6) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Mobile Safari/537.36"
        )
    },
    "extractor_args": {
        "youtube": "player_client=android"
    },
    "quiet": True,
}
ytdl = yt_dlp.YoutubeDL(ytdl_opts)

# ─── INICIALIZACIÓN DEL BOT Y COLAS ───────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix=".", intents=intents)
queues = {}  # {guild_id: [song_dict, ...]}
EMOJI_CONTROL = {'⏯️': 'toggle', '⏭️': 'skip', '⏹️': 'stop'}

# ─── FUNCIONES AUXILIARES ─────────────────────────────────────────────────────
async def get_audio_info(url: str, loop: asyncio.AbstractEventLoop):
    m = SPOT_TRACK.match(url)
    if m:
        if _spotify:
            track_id = m.group(1)
            meta = await loop.run_in_executor(None, lambda: _spotify.track(track_id))
            title = meta['name']
            artist = meta['artists'][0]['name']
            query = f"ytsearch1:{title} {artist} audio"
            res = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
            if 'entries' in res and res['entries']:
                return res['entries'][0]
            raise RuntimeError("No coincidencias en YouTube para esta pista de Spotify.")
        raise RuntimeError("🚫 Faltan credenciales de Spotify.")
    try:
        return await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
    except yt_dlp.utils.DownloadError:
        search = f"ytsearch1:{url}"
        fb = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
        if 'entries' in fb and fb['entries']:
            return fb['entries'][0]
        raise RuntimeError("No encontré alternativa en YouTube.")

async def enqueue_song(data: dict, ctx):
    title = data.get('title', 'Audio')
    audio_url = data.get('url') or data['formats'][0]['url']
    song = {'title': title, 'url': audio_url, 'channel': ctx.channel}
    vc = ctx.voice_client
    if vc.is_playing() or vc.is_paused():
        queues.setdefault(ctx.guild.id, []).append(song)
    else:
        await play_song(song, vc)

async def play_song(song_info: dict, voice_client):
    def after_play(err):
        if err: print('Error reproduciendo:', err)
        q = queues.get(song_info['channel'].guild.id, [])
        if q:
            next_song = q.pop(0)
            asyncio.run_coroutine_threadsafe(play_song(next_song, voice_client), bot.loop)
    voice_client.play(
        discord.FFmpegPCMAudio(
            song_info['url'],
            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            options='-vn'
        ), after=after_play
    )
    msg = await song_info['channel'].send(f"Reproduciendo: **{song_info['title']}**")
    for emoji in EMOJI_CONTROL:
        await msg.add_reaction(emoji)

# ─── EVENTOS Y COMANDOS ───────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

@bot.command(name='unir')
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("Únete a un canal de voz primero.")
    if ctx.voice_client:
        await ctx.voice_client.move_to(ctx.author.voice.channel)
    else:
        await ctx.author.voice.channel.connect()

@bot.command(name='reproducir', aliases=['p'])
async def play(ctx, *, url: str):
    if not ctx.author.voice:
        return await ctx.send("Únete a un canal de voz.")
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
    loop = asyncio.get_event_loop()
    # Intento extraer info inicial
    try:
        info = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
    except yt_dlp.utils.DownloadError:
        info = None

    # YouTube playlist: play first, enqueue rest and then send summary
    if info and 'entries' in info:
        entries = info['entries']
        # Reproducir primera pista
        await enqueue_song(entries[0], ctx)
        # Cargar resto y al final enviar resumen
        async def load_rest(rest):
            queued_titles = []
            for e in rest:
                await asyncio.sleep(1)
                await enqueue_song(e, ctx)
                queued_titles.append(e.get('title', '<sin título>'))
            # Enviar listado en Markdown una vez encoladas todas
            md = "**Siguiente en cola:**\n```"
            for i, title in enumerate(queued_titles, 1):
                md += f"\n{i}. {title}"
            md += "\n```"
            await ctx.send(md)
        bot.loop.create_task(load_rest(entries[1:]))
        return

    # Spotify playlist: play first, enqueue rest and then send summary
    m_pl = SPOT_PLAYLIST.match(url)
    if m_pl and _spotify:
        pid = m_pl.group(1)
        pl = await loop.run_in_executor(None, lambda: _spotify.playlist_tracks(pid))
        items = pl['items']
        # Convertir primero y reproducir
        first = items[0]['track']
        entry = await get_audio_info(first['external_urls']['spotify'], loop)
        await enqueue_song(entry, ctx)
        # Carga y resumen
        async def load_spotify(rest_items):
            queued = []
            for it in rest_items:
                await asyncio.sleep(1)
                t = it['track']
                e = await get_audio_info(t['external_urls']['spotify'], loop)
                await enqueue_song(e, ctx)
                queued.append(e.get('title', '<sin título>'))
            md = "**Siguiente en cola:**\n```"
            for i, title in enumerate(queued, 1):
                md += f"\n{i}. {title}"
            md += "\n```"
            await ctx.send(md)
        bot.loop.create_task(load_spotify(items[1:]))
        return

    # Single track or fallback
    if info and not 'entries':
        data = info
    else:
        try:
            data = await get_audio_info(url, loop)
        except Exception as e:
            return await ctx.send(f"Error: {e}")
    await enqueue_song(data, ctx)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot: return
    msg = reaction.message
    if msg.author.id != bot.user.id: return
    act = EMOJI_CONTROL.get(str(reaction.emoji))
    if not act: return
    vc = discord.utils.get(bot.voice_clients, guild=msg.guild)
    if not vc: return
    try:
        if act == 'toggle':
            if vc.is_playing(): vc.pause(); await msg.channel.send(f"{user.mention} pausó la música.")
            else: vc.resume(); await msg.channel.send(f"{user.mention} reanudó la música.")
        elif act == 'skip': vc.stop(); await msg.channel.send(f"{user.mention} saltó la canción.")
        elif act == 'stop': queues.pop(msg.guild.id, None); vc.stop(); await vc.disconnect(); await msg.channel.send(f"{user.mention} detuvo la música y desconectó el bot.")
    except Exception as e:
        await msg.channel.send(f"Control error: {e}")
    finally:
        await reaction.remove(user)

bot.run(TOKEN)
