import asyncio
import os
import shutil
import ctypes
import ctypes.util
import random
from collections import deque

import aiohttp
import discord
from discord.ext import commands
import yt_dlp

# =========================================================
# HSL-CORP ULTRA FAST & FIXED MUSIC SYSTEM
# =========================================================

def load_opus():
    if discord.opus.is_loaded():
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
                return True
        except Exception:
            pass
    return False

load_opus()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if __file__ else os.getcwd()
COOKIE_PATH = os.path.join(BASE_DIR, "cookies.txt")
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES")
COOKIE_FILE = None

if os.path.isfile(COOKIE_PATH):
    COOKIE_FILE = COOKIE_PATH
elif YOUTUBE_COOKIES:
    try:
        cookie_dir = "/tmp" if os.name != "nt" else BASE_DIR
        COOKIE_FILE = os.path.join(cookie_dir, "youtube_cookies.txt")
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(YOUTUBE_COOKIES)
    except Exception:
        pass

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
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "source_address": "0.0.0.0",
    "socket_timeout": 10,
    "retries": 3,
    "default_search": "ytsearch",
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
            await interaction.followup.send("⏸️ Paused!", ephemeral=True)
        elif self.cog.voice.is_paused():
            self.cog.voice.resume()
            button.emoji = "⏸️"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("▶️ Resumed!", ephemeral=True)

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
        self.loop = False
        self.autoplay = True
        self.starting = False
        self.play_token = 0
        self.play_lock = asyncio.Lock()
        self.autoplay_history = deque(maxlen=30)

    def invalidate_playback(self):
        self.play_token += 1
        return self.play_token

    async def update_voice_status(self, text):
        if not self.voice or not self.voice.is_connected() or not self.voice.channel:
            return
        url = f"https://discord.com/api/v10/channels/{self.voice.channel.id}/voice-status"
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
        url = f"https://discord.com/api/v10/channels/{self.voice.channel.id}/voice-status"
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
                return {
                    "title": info.get("title", "Unknown Song"),
                    "url": info.get("webpage_url") or info.get("url"),
                    "thumbnail": info.get("thumbnail"),
                    "stream_url": info.get("url")
                }
            except Exception as e:
                print(f"[MUSIC] Resolve Error: {e}")
                return None
        data = await loop.run_in_executor(None, extract)
        if not data:
            return None
        song = Song(data["title"], data["url"], data["thumbnail"], requester)
        song.stream_url = data["stream_url"]
        return song

    async def resolve_autoplay_song(self):
        if not self.current:
            return None
        loop = asyncio.get_running_loop()
        requester = self.current.requester
        queries = ["Hindi songs", "Bollywood romantic songs", "Trending music"]
        query = random.choice(queries)

        def extract():
            options = self.get_ytdlp_options()
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                if not info or "entries" not in info:
                    return None
                entries = [e for e in info.get("entries", []) if e]
                for entry in entries:
                    url = entry.get("webpage_url") or entry.get("url")
                    if url and url not in self.autoplay_history:
                        return {
                            "title": entry.get("title", "Unknown Song"),
                            "url": url,
                            "thumbnail": entry.get("thumbnail"),
                            "stream_url": entry.get("url")
                        }
            except Exception:
                pass
            return None

        data = await loop.run_in_executor(None, extract)
        if not data:
            return None
        song = Song(data["title"], data["url"], data["thumbnail"], requester)
        song.stream_url = data["stream_url"]
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
                        await asyncio.sleep(0.1)

                    stream_url = song.stream_url if hasattr(song, "stream_url") else None
                    if not stream_url:
                        res = await self.resolve_song(song.url, song.requester)
                        if res:
                            stream_url = res.stream_url

                    if not stream_url or token != self.play_token:
                        continue

                    before_options = (
                        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 "
                        "-probesize 32000 -analyzeduration 0"
                    )
                    ffmpeg_options = "-vn -loglevel error"

                    try:
                        source = await discord.FFmpegOpusAudio.from_probe(
                            stream_url,
                            executable=FFMPEG_PATH,
                            before_options=before_options,
                            options=ffmpeg_options
                        )
                    except Exception:
                        source = discord.FFmpegPCMAudio(
                            stream_url,
                            executable=FFMPEG_PATH,
                            before_options=before_options,
                            options=ffmpeg_options
                        )

                    def after_play(error):
                        if token == self.play_token:
                            self.bot.loop.call_soon_threadsafe(
                                lambda: asyncio.create_task(self.play_next())
                            )

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

    # Hybrid Support (Works with prefix `!play` AND slash `/play`)
    @commands.hybrid_command(name="play", description="Play any song from YouTube")
    async def play(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Channel Join Karo Pehle!")

        if ctx.interaction:
            await ctx.interaction.response.defer()

        self.text_channel = ctx.channel
        if not ctx.voice_client:
            self.voice = await ctx.author.voice.channel.connect()
        else:
            self.voice = ctx.voice_client

        song = await self.resolve_song(query, ctx.author)
        if not song:
            return await ctx.send("❌ Song Nahi Mila!")

        self.queue.append(song)
        await ctx.send(f"🎵 Added **{song.title}** to queue!")
        if not self.voice.is_playing() and not self.voice.is_paused():
            await self.play_next()

    @commands.hybrid_command(name="skip", description="Skip the currently playing song")
    async def skip(self, ctx):
        if not self.voice or not self.voice.is_connected():
            return await ctx.send("❌ Bot VC mein nahi hai.")
        self.invalidate_playback()
        if self.voice.is_playing() or self.voice.is_paused():
            self.voice.stop()
        await ctx.send("⏭️ Skipped!")
        await self.play_next()

    @commands.hybrid_command(name="autoplay", description="Toggle autoplay mode")
    async def autoplay_cmd(self, ctx):
        self.autoplay = not self.autoplay
        await ctx.send(f"📻 Autoplay **{'enabled' if self.autoplay else 'disabled'}**.")

    @commands.hybrid_command(name="pause", description="Pause current music")
    async def pause(self, ctx):
        if self.voice and self.voice.is_playing():
            self.voice.pause()
            await ctx.send("⏸️ Paused.")

    @commands.hybrid_command(name="resume", description="Resume paused music")
    async def resume(self, ctx):
        if self.voice and self.voice.is_paused():
            self.voice.resume()
            await ctx.send("▶️ Resumed.")

    @commands.hybrid_command(name="stop", description="Stop music and clear queue")
    async def stop(self, ctx):
        self.invalidate_playback()
        self.queue.clear()
        self.current = None
        if self.voice:
            if self.voice.is_playing() or self.voice.is_paused():
                self.voice.stop()
            await self.clear_voice_status()
        await ctx.send("⏹️ Stopped.")

    @commands.hybrid_command(name="leave", description="Disconnect bot from VC")
    async def leave(self, ctx):
        self.invalidate_playback()
        self.queue.clear()
        if self.voice:
            await self.clear_voice_status()
            await self.voice.disconnect()
            self.voice = None
        await ctx.send("👋 Disconnected!")

async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))