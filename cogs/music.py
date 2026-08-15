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
# HSL-CORP ULTRA FAST MUSIC SYSTEM
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

# High-Speed YTDLP Configuration
YTDLP_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "source_address": "0.0.0.0",
    "extract_flat": False,
    "skip_download": True,
    "socket_timeout": 10,
    "retries": 2,
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
    },
}

class Song:
    def __init__(self, title, url, thumbnail, requester):
        self.title = title
        self.url = url
        self.thumbnail = thumbnail
        self.requester = requester


class MusicButtons(discord.ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=None)
        self.cog = cog
        self.ctx = ctx

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.secondary)
    async def pause_resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cog.voice or not self.cog.voice.is_connected():
            return await interaction.response.send_message("❌ Bot VC mein nahi hai!", ephemeral=True)
        
        if self.cog.voice.is_playing():
            self.cog.voice.pause()
            button.emoji = "▶️"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("⏸️ Paused playback!", ephemeral=True)
        elif self.cog.voice.is_paused():
            self.cog.voice.resume()
            button.emoji = "⏸️"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("▶️ Resumed playback!", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary)
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏭️ Skipping...", ephemeral=True)
        await self.cog.skip(self.ctx)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏹️ Stopped!", ephemeral=True)
        await self.cog.stop(self.ctx)

    @discord.ui.button(emoji="🔂", style=discord.ButtonStyle.secondary)
    async def loop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cog.loop = not self.cog.loop
        status = "enabled" if self.cog.loop else "disabled"
        await interaction.response.send_message(f"🔂 Loop **{status}**!", ephemeral=True)


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
        except Exception:
            pass

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
        except Exception:
            pass

    def get_ytdlp_options(self):
        options = dict(YTDLP_OPTIONS)
        if COOKIE_FILE and os.path.isfile(COOKIE_FILE):
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
                options = self.get_ytdlp_options()
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(target, download=False)
                if not info:
                    return None
                if "entries" in info:
                    entries = [e for e in info.get("entries", []) if e]
                    if not entries:
                        return None
                    info = entries[0]
                webpage_url = info.get("webpage_url") or info.get("original_url") or f"https://www.youtube.com/watch?v={info.get('id')}"
                return {
                    "title": info.get("title", "Unknown Song"),
                    "url": webpage_url,
                    "thumbnail": info.get("thumbnail"),
                }
            except Exception as e:
                print(f"[MUSIC] [ERROR] Fast resolve failed: {e}")
                return None
        data = await loop.run_in_executor(None, extract)
        if not data:
            return None
        return Song(data["title"], data["url"], data["thumbnail"], requester)

    async def get_audio_stream(self, song):
        loop = asyncio.get_running_loop()
        def extract():
            try:
                options = self.get_ytdlp_options()
                options["format"] = "bestaudio/best"
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(song.url, download=False)
                if "entries" in info:
                    info = info["entries"][0]
                return info.get("url")
            except Exception as e:
                print(f"[MUSIC] [ERROR] Fast Stream extract failed: {e}")
                return None
        return await loop.run_in_executor(None, extract)

    async def resolve_autoplay_song(self):
        if not self.current:
            return None
        loop = asyncio.get_running_loop()
        requester = self.current.requester
        previous_url = self.current.url
        autoplay_queries = ["Hindi songs", "Bollywood songs", "trending music"]
        query = random.choice(autoplay_queries)

        def extract():
            options = self.get_ytdlp_options()
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                if not info or "entries" not in info:
                    return None
                entries = [e for e in info.get("entries", []) if e]
                for entry in entries:
                    url = entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                    if url != previous_url and url not in self.autoplay_history:
                        return {
                            "title": entry.get("title", "Unknown Song"),
                            "url": url,
                            "thumbnail": entry.get("thumbnail"),
                        }
            except Exception:
                pass
            return None

        data = await loop.run_in_executor(None, extract)
        if not data:
            return None
        song = Song(data["title"], data["url"], data.get("thumbnail"), requester)
        self.autoplay_history.append(song.url)
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

                    stream_url = await self.get_audio_stream(song)
                    if token != self.play_token or not stream_url:
                        if self.queue:
                            continue
                        self.current = None
                        return

                    # Fast-buffering FFmpeg parameters
                    before_options = (
                        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 "
                        "-probesize 32000 -analyzeduration 0 -nostdin"
                    )
                    ffmpeg_options = "-vn -loglevel error -ar 48000 -ac 2"

                    source = discord.FFmpegPCMAudio(
                        stream_url,
                        executable=FFMPEG_PATH,
                        before_options=before_options,
                        options=ffmpeg_options
                    )
                    source = discord.PCMVolumeTransformer(source, volume=self.volume)

                    def after_play(error):
                        if token == self.play_token and not self.stopping:
                            self.bot.loop.call_soon_threadsafe(lambda: asyncio.create_task(self.play_next()))

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
                        
                        view = MusicButtons(self, self.text_channel)
                        try:
                            await self.text_channel.send(embed=embed, view=view)
                        except Exception:
                            pass
                    break
            finally:
                self.starting = False

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Voice Channel join karo pehle!")

        self.text_channel = ctx.channel
        if not ctx.voice_client:
            self.voice = await ctx.author.voice.channel.connect()
        else:
            self.voice = ctx.voice_client

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
            return await ctx.send("❌ Bot VC mein nahi hai.")
        async with self.skip_lock:
            self.invalidate_playback()
            if self.voice.is_playing() or self.voice.is_paused():
                self.voice.stop()
            await ctx.send("⏭️ Skipped!")
            await self.play_next()

    @commands.command(name="pause")
    async def pause(self, ctx):
        if self.voice and self.voice.is_playing():
            self.voice.pause()
            await ctx.send("⏸️ Paused.")

    @commands.command(name="resume")
    async def resume(self, ctx):
        if self.voice and self.voice.is_paused():
            self.voice.resume()
            await ctx.send("▶️ Resumed.")

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
        await ctx.send("⏹️ Stopped.")

    @commands.command(name="queue", aliases=["q"])
    async def queue_info(self, ctx):
        if not self.current and not self.queue:
            return await ctx.send("📂 Queue empty hai!")
        embed = discord.Embed(title="Current Music Queue", color=discord.Color.purple())
        if self.current:
            embed.add_field(name="Now Playing", value=f"[{self.current.title}]({self.current.url})", inline=False)
        if self.queue:
            queue_list = "\n".join([f"`{i+1}.` [{s.title}]({s.url})" for i, s in enumerate(list(self.queue)[:10])])
            embed.add_field(name="Up Next", value=queue_list, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="loop")
    async def loop(self, ctx):
        self.loop = not self.loop
        await ctx.send(f"🔂 Looping **{'enabled' if self.loop else 'disabled'}**.")

    @commands.command(name="autoplay")
    async def autoplay_cmd(self, ctx):
        self.autoplay = not self.autoplay
        await ctx.send(f"📻 Autoplay **{'enabled' if self.autoplay else 'disabled'}**.")

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