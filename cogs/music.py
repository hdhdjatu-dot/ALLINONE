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
# HSL-CORP ULTRA FIXED MUSIC SYSTEM
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

class Song:
    def __init__(self, title, url, thumbnail, requester, stream_url=None):
        self.title = title
        self.url = url
        self.thumbnail = thumbnail
        self.requester = requester
        self.stream_url = stream_url


class MusicButtons(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Pause", emoji="⏯️", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cog.voice or not self.cog.voice.is_connected():
            return await interaction.response.send_message("❌ Bot VC mein nahi hai!", ephemeral=True)
        
        if self.cog.voice.is_playing():
            self.cog.voice.pause()
            button.label = "Resume"
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.success
            await interaction.response.edit_message(embed=self.cog.build_embed(), view=self)
        elif self.cog.voice.is_paused():
            self.cog.voice.resume()
            button.label = "Pause"
            button.emoji = "⏯️"
            button.style = discord.ButtonStyle.primary
            await interaction.response.edit_message(embed=self.cog.build_embed(), view=self)

    @discord.ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.success, row=0)
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cog.voice or not self.cog.voice.is_connected():
            return await interaction.response.send_message("❌ Bot VC mein nahi hai!", ephemeral=True)
        await interaction.response.defer()
        self.cog.loop = False
        self.cog.invalidate_playback()
        if self.cog.voice.is_playing() or self.cog.voice.is_paused():
            self.cog.voice.stop()
        await self.cog.play_next()

    @discord.ui.button(label="Loop", emoji="🔄", style=discord.ButtonStyle.primary, row=0)
    async def loop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cog.loop = not self.cog.loop
        await interaction.response.edit_message(embed=self.cog.build_embed(), view=self)

    @discord.ui.button(label="Autoplay", emoji="🤖", style=discord.ButtonStyle.secondary, row=1)
    async def autoplay_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cog.autoplay = not self.cog.autoplay
        await interaction.response.edit_message(embed=self.cog.build_embed(), view=self)

    @discord.ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger, row=1)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cog.invalidate_playback()
        self.cog.queue.clear()
        self.cog.current = None
        if self.cog.voice:
            if self.cog.voice.is_playing() or self.cog.voice.is_paused():
                self.cog.voice.stop()
            await self.cog.clear_voice_status()
        if self.cog.now_playing_msg:
            try:
                embed = discord.Embed(
                    title="🎶 HSL-CORP MUSIC",
                    description="⏹️ **Playback Stopped and Queue Cleared**",
                    color=discord.Color.red()
                )
                await self.cog.now_playing_msg.edit(embed=embed, view=None)
            except Exception:
                pass
        await interaction.response.send_message("⏹️ Playback stopped!", ephemeral=True)


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
        self.now_playing_msg = None

    def invalidate_playback(self):
        self.play_token += 1
        return self.play_token

    def build_embed(self):
        if not self.current:
            return discord.Embed(title="🎶 HSL-CORP MUSIC", description="No song currently playing.", color=discord.Color.blue())
        
        loop_status = "🔴 OFF" if not self.loop else "🟢 ON"
        autoplay_status = "🟢 ON" if self.autoplay else "🔴 OFF"

        description = (
            f"### 🎶 NOW PLAYING\n\n"
            f"**[{self.current.title}]({self.current.url})**\n\n"
            f"-----------------------------------------\n"
            f"👤 **Requested by:** {self.current.requester.mention}\n"
            f"🔊 **Volume:** 100%\n"
            f"🔄 **Loop:** {loop_status}\n"
            f"🤖 **Autoplay:** {autoplay_status}\n"
            f"-----------------------------------------"
        )

        embed = discord.Embed(
            title="🎶 HSL-CORP MUSIC",
            description=description,
            color=discord.Color.blue()
        )
        if self.current.thumbnail:
            embed.set_thumbnail(url=self.current.thumbnail)
        
        embed.set_footer(text="HSL & CORPORATION • Music System")
        return embed

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
        opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
            "skip_download": True,
            "socket_timeout": 10,
            "source_address": "0.0.0.0",
            "nocheckcertificate": True,
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                }
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
        }
        if COOKIE_FILE and os.path.isfile(COOKIE_FILE):
            opts["cookiefile"] = COOKIE_FILE
        return opts

    async def resolve_song(self, search_query, requester):
        loop = asyncio.get_running_loop()

        def extract():
            query = str(search_query).strip()
            if not query:
                return None
            
            target = query if query.startswith(("http://", "https://")) else f"ytsearch1:{query}"
            opts = self.get_ytdlp_options()

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(target, download=False)
                if not info:
                    return None
                if "entries" in info:
                    entries = [e for e in info.get("entries", []) if e]
                    if not entries:
                        return None
                    info = entries[0]

                title = info.get("title", "Unknown Song")
                webpage_url = info.get("webpage_url") or f"https://www.youtube.com/watch?v={info.get('id')}"
                thumbnail = info.get("thumbnail")
                stream_url = info.get("url")

                if stream_url:
                    return {
                        "title": title,
                        "url": webpage_url,
                        "thumbnail": thumbnail,
                        "stream_url": stream_url
                    }
            except Exception as e:
                print(f"[MUSIC] Extraction error: {e}")
            return None

        data = await loop.run_in_executor(None, extract)
        if not data:
            return None
        return Song(data["title"], data["url"], data["thumbnail"], requester, stream_url=data["stream_url"])

    async def resolve_autoplay_song(self):
        if not self.current:
            return None
        loop = asyncio.get_running_loop()
        requester = self.current.requester
        queries = [
            f"{self.current.title} song", 
            "Trending Bollywood Songs", 
            "Arijit Singh Latest Songs", 
            "Hindi Pop Romantic Mix"
        ]
        query = random.choice(queries)

        def extract():
            opts = self.get_ytdlp_options()
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                if not info or "entries" not in info:
                    return None
                entries = [e for e in info.get("entries", []) if e]
                for entry in entries:
                    url = entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                    if url and url not in self.autoplay_history and url != self.current.url:
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
        song = Song(data["title"], data["url"], data["thumbnail"], requester, stream_url=data["stream_url"])
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

                    stream_url = song.stream_url
                    if not stream_url:
                        res = await self.resolve_song(song.url, song.requester)
                        if res:
                            stream_url = res.stream_url

                    if not stream_url or token != self.play_token:
                        continue

                    before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -probesize 32000 -analyzeduration 0"
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

                    embed = self.build_embed()
                    view = MusicButtons(self)

                    if self.now_playing_msg:
                        try:
                            await self.now_playing_msg.edit(embed=embed, view=view)
                        except Exception:
                            self.now_playing_msg = await self.text_channel.send(embed=embed, view=view)
                    elif self.text_channel:
                        self.now_playing_msg = await self.text_channel.send(embed=embed, view=view)
                    break
            finally:
                self.starting = False

    @commands.hybrid_command(name="play", aliases=["p"], description="Play any song from YouTube")
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

        msg = await ctx.send("🔍 Searching song...")
        song = await self.resolve_song(query, ctx.author)
        
        if not song:
            return await msg.edit(content="❌ **Song Nahi Mila!** Please try pasting full YouTube URL or check search query.")

        await msg.delete()
        self.queue.append(song)
        
        if not self.voice.is_playing() and not self.voice.is_paused():
            await self.play_next()
        else:
            await ctx.send(f"🎵 Added **{song.title}** to queue!", delete_after=5)

    @commands.hybrid_command(name="skip", aliases=["s"], description="Skip current song")
    async def skip(self, ctx):
        if not self.voice or not self.voice.is_connected():
            return await ctx.send("❌ Bot VC mein nahi hai.")
        self.loop = False
        self.invalidate_playback()
        if self.voice.is_playing() or self.voice.is_paused():
            self.voice.stop()
        await ctx.send("⏭️ Skipped!", delete_after=3)
        await self.play_next()

    @commands.hybrid_command(name="autoplay", description="Toggle autoplay mode")
    async def autoplay_cmd(self, ctx):
        self.autoplay = not self.autoplay
        if self.now_playing_msg:
            await self.now_playing_msg.edit(embed=self.build_embed())
        await ctx.send(f"🤖 Autoplay **{'enabled' if self.autoplay else 'disabled'}**.", delete_after=5)

    @commands.hybrid_command(name="pause", description="Pause music")
    async def pause(self, ctx):
        if self.voice and self.voice.is_playing():
            self.voice.pause()
            if self.now_playing_msg:
                await self.now_playing_msg.edit(embed=self.build_embed())
            await ctx.send("⏸️ Paused.", delete_after=3)

    @commands.hybrid_command(name="resume", description="Resume music")
    async def resume(self, ctx):
        if self.voice and self.voice.is_paused():
            self.voice.resume()
            if self.now_playing_msg:
                await self.now_playing_msg.edit(embed=self.build_embed())
            await ctx.send("▶️ Resumed.", delete_after=3)

    @commands.hybrid_command(name="stop", description="Stop music and clear queue")
    async def stop(self, ctx):
        self.invalidate_playback()
        self.queue.clear()
        self.current = None
        if self.voice:
            if self.voice.is_playing() or self.voice.is_paused():
                self.voice.stop()
            await self.clear_voice_status()
        if self.now_playing_msg:
            try:
                embed = discord.Embed(
                    title="🎶 HSL-CORP MUSIC",
                    description="⏹️ **Playback Stopped and Queue Cleared**",
                    color=discord.Color.red()
                )
                await self.now_playing_msg.edit(embed=embed, view=None)
            except Exception:
                pass
        await ctx.send("⏹️ Stopped.", delete_after=5)

    @commands.hybrid_command(name="leave", aliases=["dc"], description="Disconnect bot")
    async def leave(self, ctx):
        self.invalidate_playback()
        self.queue.clear()
        self.current = None
        if self.voice:
            await self.clear_voice_status()
            await self.voice.disconnect()
            self.voice = None
        if self.now_playing_msg:
            try:
                await self.now_playing_msg.delete()
            except Exception:
                pass
            self.now_playing_msg = None
        await ctx.send("👋 Disconnected!", delete_after=5)

async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))