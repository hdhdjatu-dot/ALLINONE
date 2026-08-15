import asyncio
import os
import shutil
import ctypes
import ctypes.util
import random
import time
from collections import deque

import aiohttp
import discord
from discord.ext import commands
import yt_dlp

# =========================================================
# HSL-CORP ULTRA MUSIC SYSTEM
# =========================================================

def load_opus():
    if discord.opus.is_loaded():
        print("[MUSIC] [OK] Opus already loaded.")
        return True

    possible_paths = [
        ctypes.util.find_library("opus"),
        "libopus.so.0",
        "libopus.so",
        "/usr/lib/x86_64-linux-gnu/libopus.so.0",
        "/usr/lib/aarch64-linux-gnu/libopus.so.0",
    ]

    for path in possible_paths:
        if not path:
            continue
        try:
            ctypes.CDLL(path)
            discord.opus.load_opus(path)
            if discord.opus.is_loaded():
                print(f"[MUSIC] [OK] Opus loaded: {path}")
                return True
        except Exception as e:
            print(f"[MUSIC] [WARN] Failed to load Opus {path}: {e}")

    print("[MUSIC] [ERROR] Opus codec NOT loaded.")
    return False

OPUS_LOADED = load_opus()

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
) if __file__ else os.getcwd()

COOKIE_PATH = os.path.join(BASE_DIR, "cookies.txt")
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES")
COOKIE_FILE = None

if os.path.isfile(COOKIE_PATH):
    COOKIE_FILE = COOKIE_PATH
    print(f"[MUSIC] [COOKIE] Local cookies found: {COOKIE_FILE}")
elif YOUTUBE_COOKIES:
    try:
        cookie_dir = "/tmp" if os.name != "nt" else BASE_DIR
        COOKIE_FILE = os.path.join(cookie_dir, "youtube_cookies.txt")
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(YOUTUBE_COOKIES)
        print("[MUSIC] [COOKIE] Cookies loaded from environment.")
    except Exception as e:
        print(f"[MUSIC] [ERROR] Cookie file error: {e!r}")
else:
    print("[MUSIC] [WARN] YouTube cookies not found.")

HSL_GIF = (
    "https://media3.giphy.com/media/"
    "v1.Y2lkPTc5MGI3NjExZ3RqemR3c3A0MHl3NWw1NHE4a2FjdWVkdDdqdXppaXdxdHhobGF5ayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/"
    "iBILBPeCHDVuELjOND/giphy.gif"
)

def find_ffmpeg():
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]
    for path in paths:
        if os.path.isfile(path):
            return path
    return "ffmpeg"

FFMPEG_PATH = find_ffmpeg()

YTDLP_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "source_address": "0.0.0.0",
    "js_runtimes": {"deno": {}},
    "remote_components": ["ejs:github"],
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    },
    "socket_timeout": 20,
    "retries": 3,
    "fragment_retries": 3,
    "concurrent_fragment_downloads": 1,
    "ignoreerrors": False,
}

class Song:
    def __init__(self, title, url, thumbnail, requester):
        self.title = title
        self.url = url
        self.thumbnail = thumbnail
        self.requester = requester

class MusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice = None
        self.text_channel = None
        self.queue = deque()
        self.current = None
        self.volume = 1.0
        self.loop = False
        self.autoplay = True
        self.starting = False
        self.play_token = 0
        self.play_lock = asyncio.Lock()
        self.skip_lock = asyncio.Lock()
        self.now_playing_message = None
        self.autoplay_history = deque(maxlen=30)
        self.play_history = deque(maxlen=30)
        self.stopping = False

    def invalidate_playback(self):
        self.play_token += 1
        return self.play_token

    async def update_voice_status(self, text):
        if not self.voice or not self.voice.is_connected() or not self.voice.channel:
            return
        channel_id = self.voice.channel.id
        url = f"https://discord.com/api/v10/channels/{channel_id}/voice-status"
        headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                await session.put(url, headers=headers, json={"status": str(text)[:500]})
        except Exception as e:
            print(f"[MUSIC] [WARN] VC status error: {e!r}")

    async def clear_voice_status(self):
        if not self.voice or not self.voice.channel:
            return
        channel_id = self.voice.channel.id
        url = f"https://discord.com/api/v10/channels/{channel_id}/voice-status"
        headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                await session.put(url, headers=headers, json={"status": ""})
        except Exception as e:
            print(f"[MUSIC] [WARN] VC status clear error: {e!r}")

    def get_ytdlp_options(self, use_cookies=True):
        options = dict(YTDLP_OPTIONS)
        options["http_headers"] = dict(YTDLP_OPTIONS["http_headers"])
        options["js_runtimes"] = {"deno": {}}
        options["remote_components"] = ["ejs:github"]
        if use_cookies and COOKIE_FILE and os.path.isfile(COOKIE_FILE):
            options["cookiefile"] = COOKIE_FILE
        return options

    async def resolve_song(self, search_query, requester):
        loop = asyncio.get_running_loop()
        def extract():
            query = str(search_query).strip()
            if not query:
                return None
            target = query if query.startswith(("http://", "https://")) else f"ytsearch1:{query}"
            try:
                options = self.get_ytdlp_options(use_cookies=bool(COOKIE_FILE))
                options["skip_download"] = True
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(target, download=False)
                if not info:
                    return None
                if "entries" in info:
                    entries = [e for e in (info.get("entries") or []) if e]
                    if not entries:
                        return None
                    info = entries[0]
                webpage_url = info.get("webpage_url") or info.get("original_url")
                if not webpage_url and info.get("id"):
                    webpage_url = f"https://www.youtube.com/watch?v={info.get('id')}"
                if not webpage_url:
                    return None
                return {
                    "title": info.get("title", "Unknown Song"),
                    "url": webpage_url,
                    "thumbnail": info.get("thumbnail"),
                }
            except Exception as e:
                print(f"[MUSIC] [ERROR] YouTube resolve failed: {repr(e)}")
                return None
        data = await loop.run_in_executor(None, extract)
        if not data:
            return None
        return Song(data["title"], data["url"], data["thumbnail"], requester)

    async def get_audio_stream(self, song):
        loop = asyncio.get_running_loop()
        def extract():
            try:
                options = self.get_ytdlp_options(use_cookies=bool(COOKIE_FILE))
                options.update({
                    "skip_download": True,
                    "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
                    "noplaylist": True,
                })
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(song.url, download=False)
                if not info:
                    return None
                if "entries" in info:
                    entries = [e for e in (info.get("entries") or []) if e]
                    if not entries:
                        return None
                    info = entries[0]
                return info.get("url")
            except Exception as e:
                print(f"[MUSIC] [ERROR] Audio stream extraction failed: {repr(e)}")
                return None
        return await loop.run_in_executor(None, extract)

    async def resolve_autoplay_song(self):
        if not self.current:
            return None
        loop = asyncio.get_running_loop()
        requester = self.current.requester
        previous_url = self.current.url
        previous_title = self.current.title.lower().strip()
        autoplay_queries = [
            "Hindi songs", "Bollywood songs", "latest Hindi music",
            "popular Hindi songs", "Hindi romantic songs", "trending Bollywood songs"
        ]
        random.shuffle(autoplay_queries)
        history_urls = set(self.autoplay_history)
        recent_urls = set(self.play_history)

        def extract():
            options = self.get_ytdlp_options(use_cookies=bool(COOKIE_FILE))
            options["skip_download"] = True
            options["extract_flat"] = True
            for query in autoplay_queries:
                try:
                    with yt_dlp.YoutubeDL(options) as ydl:
                        info = ydl.extract_info(f"ytsearch10:{query}", download=False)
                    if not info:
                        continue
                    entries = info.get("entries") or []
                    valid = []
                    for entry in entries:
                        if not entry:
                            continue
                        title = entry.get("title", "").strip()
                        url = entry.get("webpage_url") or entry.get("original_url")
                        if not url and entry.get("id"):
                            url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                        if not url or url == previous_url or title.lower() == previous_title:
                            continue
                        if url in history_urls or url in recent_urls:
                            continue
                        valid.append(entry)
                    if valid:
                        entry = random.choice(valid)
                        url = entry.get("webpage_url") or entry.get("original_url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                        return {
                            "title": entry.get("title", "Unknown Song"),
                            "url": url,
                            "thumbnail": entry.get("thumbnail"),
                        }
                except Exception:
                    continue
            return None

        data = await loop.run_in_executor(None, extract)
        if not data:
            return None
        song = Song(data["title"], data["url"], data.get("thumbnail"), requester)
        self.autoplay_history.append(song.url)
        self.play_history.append(song.url)
        return song

    async def play_next(self):
        async with self.play_lock:
            if not self.voice or not self.voice.is_connected() or self.starting:
                return
            self.starting = True
            try:
                while True:
                    if not self.voice or not self.voice.is_connected():
                        return

                    if self.loop and self.current:
                        song = self.current
                    elif self.queue:
                        song = self.queue.popleft()
                        self.current = song
                        self.play_history.append(song.url)
                    elif self.autoplay and self.current:
                        song = await self.resolve_autoplay_song()
                        if not song:
                            self.current = None
                            await self.clear_voice_status()
                            return
                        self.current = song
                    else:
                        self.current = None
                        await self.clear_voice_status()
                        return

                    self.play_token += 1
                    token = self.play_token

                    if self.voice.is_playing() or self.voice.is_paused():
                        self.voice.stop()
                        await asyncio.sleep(0.08)

                    stream_url = await self.get_audio_stream(song)
                    if token != self.play_token:
                        return

                    if not stream_url:
                        if self.queue:
                            self.current = None
                            continue
                        if self.autoplay:
                            continue
                        self.current = None
                        await self.clear_voice_status()
                        return

                    before_options = (
                        "-reconnect 1 -reconnect_streamed 1 -reconnect_at_eof 1 "
                        "-reconnect_on_network_error 1 "
                        "-reconnect_on_http_error 403,404,429,500,502,503,504 "
                        "-reconnect_delay_max 2 -nostdin"
                    )
                    ffmpeg_options = "-vn -loglevel error -ar 48000 -ac 2 -bufsize 512k"

                    source = discord.FFmpegPCMAudio(
                        stream_url,
                        executable=FFMPEG_PATH,
                        before_options=before_options,
                        options=ffmpeg_options
                    )
                    source = discord.PCMVolumeTransformer(source, volume=self.volume)

                    def after_play(error):
                        def advance():
                            if token == self.play_token and not self.stopping:
                                asyncio.create_task(self.play_next())
                        self.bot.loop.call_soon_threadsafe(advance)

                    self.voice.play(source, after=after_play)
                    await self.update_voice_status(f"🎶 {song.title}")

                    if self.text_channel:
                        embed = discord.Embed(
                            title="Now Playing",
                            description=f"[{song.title}]({song.url})",
                            color=discord.Color.blue()
                        )
                        if song.thumbnail:
                            embed.set_thumbnail(url=song.thumbnail)
                        embed.set_image(url=HSL_GIF)
                        embed.set_footer(text=f"Requested by {song.requester.display_name}")
                        try:
                            await self.text_channel.send(embed=embed)
                        except Exception:
                            pass
                    break
            finally:
                self.starting = False

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Voice channel mein join hona padega!")
        self.text_channel = ctx.channel
        if not ctx.voice_client:
            self.voice = await ctx.author.voice.channel.connect()
        else:
            self.voice = ctx.voice_client

        async with ctx.typing():
            song = await self.resolve_song(query, ctx.author)
            if not song:
                return await ctx.send("❌ Song nahi mila!")
            self.queue.append(song)
            await ctx.send(f"🎵 Added **{song.title}** to queue!")
            if not self.voice.is_playing() and not self.voice.is_paused():
                await self.play_next()

    @commands.command(name="skip", aliases=["s"])
    async def skip(self, ctx):
        if not self.voice or not self.voice.is_connected():
            return await ctx.send("❌ Voice channel se connected nahi hoon.")
        async with self.skip_lock:
            self.invalidate_playback()
            if self.voice.is_playing() or self.voice.is_paused():
                self.voice.stop()
            await ctx.send("⏭️ Skipped current track.")
            await self.play_next()

    @commands.command(name="pause")
    async def pause(self, ctx):
        if self.voice and self.voice.is_playing():
            self.voice.pause()
            await ctx.send("⏸️ Paused playback.")

    @commands.command(name="resume")
    async def resume(self, ctx):
        if self.voice and self.voice.is_paused():
            self.voice.resume()
            await ctx.send("▶️ Resumed playback.")

    @commands.command(name="stop")
    async def stop(self, ctx):
        self.stopping = True
        self.invalidate_playback()
        self.queue.clear()
        self.current = None
        if self.voice:
            if self.voice.is_playing() or self.voice.is_paused():
                self.voice.stop()
            await self.clear_voice_status()
        self.stopping = False
        await ctx.send("⏹️ Stopped playback and cleared queue.")

    @commands.command(name="queue", aliases=["q"])
    async def queue_info(ctx_or_self, ctx=None):
        instance = ctx_or_self if isinstance(ctx_or_self, MusicPlayer) else None
        context = ctx if ctx else ctx_or_self
        player = instance
        if not player.current and not player.queue:
            return await context.send("📂 Queue empty hai!")
        embed = discord.Embed(title="Current Music Queue", color=discord.Color.purple())
        if player.current:
            embed.add_field(name="Now Playing", value=f"[{player.current.title}]({player.current.url})", inline=False)
        if player.queue:
            queue_list = "\n".join([f"`{i+1}.` [{s.title}]({s.url})" for i, s in enumerate(list(player.queue)[:10])])
            embed.add_field(name="Up Next", value=queue_list, inline=False)
        await context.send(embed=embed)

    @commands.command(name="loop")
    async def loop(self, ctx):
        self.loop = not self.loop
        await ctx.send(f"🔂 Looping is **{'enabled' if self.loop else 'disabled'}**.")

    @commands.command(name="autoplay")
    async def autoplay_cmd(self, ctx):
        self.autoplay = not self.autoplay
        await ctx.send(f"📻 Autoplay is **{'enabled' if self.autoplay else 'disabled'}**.")

    @commands.command(name="leave", aliases=["dc"])
    async def leave(self, ctx):
        self.stopping = True
        self.invalidate_playback()
        self.queue.clear()
        if self.voice:
            await self.clear_voice_status()
            await self.voice.disconnect()
            self.voice = None
        self.stopping = False
        await ctx.send("👋 Disconnected!")

async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))