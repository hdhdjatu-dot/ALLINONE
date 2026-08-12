import asyncio
import ctypes
import ctypes.util
import os
import shutil
import time
from collections import deque

import discord
import discord.opus
from discord.ext import commands
from discord.http import Route
import yt_dlp


# =========================================================
# HSL-CORP FAST MUSIC SYSTEM
# =========================================================


# =========================================================
# CONFIG
# =========================================================

STATUS_UPDATE_INTERVAL = 3.0

MAX_QUEUE_DISPLAY = 15

STREAM_REFRESH_AFTER = 120

FFMPEG_BEFORE_OPTIONS = (
    "-reconnect 1 "
    "-reconnect_streamed 1 "
    "-reconnect_at_eof 1 "
    "-reconnect_delay_max 5 "
    "-nostdin"
)

FFMPEG_OPTIONS = (
    "-vn "
    "-sn "
    "-dn "
    "-loglevel warning"
)


# =========================================================
# OPUS
# =========================================================

def load_opus():

    if discord.opus.is_loaded():
        print("[MUSIC] Opus already loaded.")
        return True

    possible_paths = [
        ctypes.util.find_library("opus"),
        "libopus.so.0",
        "libopus.so",
        "/usr/lib/x86_64-linux-gnu/libopus.so.0",
        "/usr/lib/aarch64-linux-gnu/libopus.so.0",
        r"C:\Program Files\opus\bin\opus.dll",
        r"C:\Program Files (x86)\opus\bin\opus.dll",
    ]

    for path in possible_paths:

        if not path:
            continue

        try:

            ctypes.CDLL(path)

            discord.opus.load_opus(path)

            if discord.opus.is_loaded():

                print(
                    f"[MUSIC] Opus loaded: {path}"
                )

                return True

        except Exception as e:

            print(
                f"[MUSIC] Opus load failed "
                f"{path}: {e}"
            )

    print("[MUSIC] Opus codec NOT loaded.")

    return False


OPUS_LOADED = load_opus()


# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# =========================================================
# YOUTUBE COOKIES
# =========================================================

COOKIE_PATH = os.path.join(
    BASE_DIR,
    "cookies.txt"
)

YOUTUBE_COOKIES = os.getenv(
    "YOUTUBE_COOKIES"
)

COOKIE_FILE = None


if os.path.isfile(COOKIE_PATH):

    COOKIE_FILE = COOKIE_PATH

    print(
        f"[MUSIC] Cookies found: "
        f"{COOKIE_FILE}"
    )

elif YOUTUBE_COOKIES:

    try:

        COOKIE_FILE = "/tmp/youtube_cookies.txt"

        with open(
            COOKIE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                YOUTUBE_COOKIES
            )

        print(
            "[MUSIC] Cookies loaded from ENV."
        )

    except Exception as e:

        print(
            "[MUSIC] Cookie error:",
            repr(e)
        )

else:

    print(
        "[MUSIC] No YouTube cookies."
    )


# =========================================================
# HSL GIF
# =========================================================

HSL_GIF = (
    "https://media3.giphy.com/media/"
    "v1.Y2lkPTc5MGI3NjExZ3RqemR3c3A0MHl3NWw1NHE4a2FjdWVkdDdqdXppaXdxdHhobGF5ayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/"
    "iBILBPeCHDVuELjOND/giphy.gif"
)


# =========================================================
# ANIMATED VOICE STATUS
# =========================================================

STATUS_FRAMES = [
    "◐",
    "◓",
    "◑",
    "◒",
]


# =========================================================
# FFMPEG
# =========================================================

def find_ffmpeg():

    ffmpeg = shutil.which(
        "ffmpeg"
    )

    if ffmpeg:

        print(
            f"[MUSIC] FFmpeg: {ffmpeg}"
        )

        return ffmpeg

    paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]

    for path in paths:

        if os.path.isfile(path):

            print(
                f"[MUSIC] FFmpeg: {path}"
            )

            return path

    print(
        "[MUSIC] FFmpeg not found. "
        "Using PATH."
    )

    return "ffmpeg"


FFMPEG_PATH = find_ffmpeg()


# =========================================================
# YT-DLP OPTIONS
# =========================================================

YTDLP_OPTIONS = {

    "quiet": True,

    "no_warnings": True,

    "noplaylist": True,

    "skip_download": True,

    "source_address": "0.0.0.0",

    "nocheckcertificate": True,

    "geo_bypass": True,

    "socket_timeout": 10,

    "retries": 2,

    "fragment_retries": 2,

    "extractor_retries": 2,

    "continuedl": False,

    "concurrent_fragment_downloads": 4,

    "format": (
        "bestaudio[ext=webm]/"
        "bestaudio[ext=m4a]/"
        "bestaudio/best"
    ),

    "http_headers": {

        "User-Agent":
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 "
            "Safari/537.36"
    }
}


if COOKIE_FILE:

    YTDLP_OPTIONS[
        "cookiefile"
    ] = COOKIE_FILE


# =========================================================
# DURATION
# =========================================================

def format_duration(seconds):

    try:

        seconds = int(
            seconds or 0
        )

    except Exception:

        return "LIVE"

    if seconds <= 0:

        return "LIVE"

    hours, remainder = divmod(
        seconds,
        3600
    )

    minutes, seconds = divmod(
        remainder,
        60
    )

    if hours:

        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    return (
        f"{minutes}:"
        f"{seconds:02d}"
    )


# =========================================================
# SONG
# =========================================================

class Song:

    def __init__(
        self,
        title,
        url,
        stream_url,
        thumbnail,
        duration,
        requester,
        http_headers=None
    ):

        self.title = title

        self.url = url

        self.stream_url = stream_url

        self.thumbnail = thumbnail

        self.duration = duration or 0

        self.requester = requester

        self.http_headers = (
            http_headers or {}
        )

        self.resolved_at = time.monotonic()


# =========================================================
# MUSIC PLAYER
# =========================================================

class MusicPlayer:

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        self.voice = None

        # IMPORTANT:
        # This will always be the VoiceChannel.
        # Messages will appear in Voice Channel Text Chat.
        self.text_channel = None

        self.voice_channel = None

        self.queue = deque()

        self.current = None

        self.volume = 1.0

        self.loop = False

        self.autoplay = True

        self.starting = False

        self.play_token = 0

        self.now_playing_message = None

        self.status_task = None

        self.status_frame = 0

        self.started_at = None


    # =====================================================
    # VOICE CONNECTION
    # =====================================================

    async def connect_to(
        self,
        voice_channel
    ):

        try:

            current = self.voice

            if current:

                if not current.is_connected():

                    self.voice = None

                    current = None

            if current:

                if current.channel != voice_channel:

                    await current.move_to(
                        voice_channel
                    )

            else:

                self.voice = (
                    await voice_channel.connect(
                        reconnect=True,
                        timeout=10
                    )
                )

            self.voice_channel = (
                voice_channel
            )

            self.text_channel = (
                voice_channel
            )

            return True

        except Exception as e:

            print(
                "[MUSIC] VOICE CONNECT ERROR:",
                repr(e)
            )

            return False


    # =====================================================
    # SET VOICE CHANNEL STATUS
    # =====================================================

    async def set_channel_status(
        self,
        channel,
        status
    ):

        if not channel:

            return False

        try:

            # Discord API:
            # PUT /channels/{channel.id}/voice-status

            route = Route(
                "PUT",
                "/channels/{channel_id}/voice-status",
                channel_id=channel.id
            )

            await self.bot.http.request(
                route,
                json={
                    "status": status
                }
            )

            return True

        except Exception as e:

            print(
                "[MUSIC] STATUS ERROR:",
                repr(e)
            )

            return False


    # =====================================================
    # START STATUS ANIMATION
    # =====================================================

    async def start_status_animation(
        self,
        song
    ):

        await self.stop_status_animation(
            clear_status=False
        )

        if not self.voice_channel:

            return

        self.status_frame = 0

        self.status_task = asyncio.create_task(
            self.status_loop(song)
        )


    # =====================================================
    # STATUS LOOP
    # =====================================================

    async def status_loop(
        self,
        song
    ):

        try:

            while True:

                if not self.voice:

                    break

                if not self.voice.is_connected():

                    break

                if self.current is not song:

                    break

                frame = STATUS_FRAMES[
                    self.status_frame
                    % len(STATUS_FRAMES)
                ]

                self.status_frame += 1

                title = song.title.strip()

                # Discord status maximum is 500 chars.
                title = title[:460]

                status = (
                    f"{frame} 🎵 {title}"
                )

                await self.set_channel_status(
                    self.voice_channel,
                    status
                )

                await asyncio.sleep(
                    STATUS_UPDATE_INTERVAL
                )

        except asyncio.CancelledError:

            return

        except Exception as e:

            print(
                "[MUSIC] STATUS LOOP ERROR:",
                repr(e)
            )


    # =====================================================
    # STOP STATUS
    # =====================================================

    async def stop_status_animation(
        self,
        clear_status=True
    ):

        task = self.status_task

        self.status_task = None

        if task:

            if task is not asyncio.current_task():

                task.cancel()

                try:

                    await task

                except asyncio.CancelledError:

                    pass

                except Exception:

                    pass

        if clear_status:

            if self.voice_channel:

                await self.set_channel_status(
                    self.voice_channel,
                    None
                )


    # =====================================================
    # RESOLVE SONG
    # =====================================================

    async def resolve_song(
        self,
        query,
        requester
    ):

        query = str(
            query
        ).strip()

        if not query:

            return None

        loop = asyncio.get_running_loop()

        def extract():

            options = dict(
                YTDLP_OPTIONS
            )

            target = query

            if not query.startswith(
                (
                    "http://",
                    "https://"
                )
            ):

                target = (
                    f"ytsearch1:{query}"
                )

                print(
                    "[MUSIC] SEARCH:",
                    query
                )

            else:

                print(
                    "[MUSIC] URL:",
                    query
                )

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                info = ydl.extract_info(
                    target,
                    download=False
                )

            if not info:

                return None

            if info.get("entries"):

                entries = [
                    entry
                    for entry in info["entries"]
                    if entry
                ]

                if not entries:

                    return None

                info = entries[0]

            stream_url = info.get(
                "url"
            )

            if not stream_url:

                return None

            webpage_url = (
                info.get("webpage_url")
                or info.get("original_url")
                or query
            )

            headers = (
                info.get(
                    "http_headers"
                )
                or {}
            )

            return {

                "title":
                    info.get(
                        "title",
                        "Unknown Song"
                    ),

                "url":
                    webpage_url,

                "stream_url":
                    stream_url,

                "thumbnail":
                    info.get(
                        "thumbnail"
                    ),

                "duration":
                    info.get(
                        "duration",
                        0
                    ),

                "http_headers":
                    headers
            }

        try:

            data = await loop.run_in_executor(
                None,
                extract
            )

        except Exception as e:

            print(
                "[MUSIC] RESOLVE ERROR:",
                repr(e)
            )

            return None

        if not data:

            return None

        duration = format_duration(
            data["duration"]
        )

        print(
            f"[MUSIC] READY: "
            f"{data['title']} "
            f"[{duration}]"
        )

        return Song(
            data["title"],
            data["url"],
            data["stream_url"],
            data["thumbnail"],
            data["duration"],
            requester,
            data["http_headers"]
        )


    # =====================================================
    # REFRESH OLD STREAM
    # =====================================================

    async def refresh_song(
        self,
        song
    ):

        age = (
            time.monotonic()
            - song.resolved_at
        )

        if age < STREAM_REFRESH_AFTER:

            return song

        print(
            "[MUSIC] Refreshing expired stream:",
            song.title
        )

        refreshed = await self.resolve_song(
            song.url,
            song.requester
        )

        if refreshed:

            refreshed.title = song.title

            if not refreshed.thumbnail:

                refreshed.thumbnail = (
                    song.thumbnail
                )

            return refreshed

        return song


    # =====================================================
    # BUILD FFMPEG HEADERS
    # =====================================================

    def build_headers(
        self,
        song
    ):

        headers = song.http_headers

        if not headers:

            return ""

        selected = {}

        for key, value in headers.items():

            key_lower = key.lower()

            if key_lower in (
                "user-agent",
                "referer"
            ):

                selected[key] = value

        if not selected:

            return ""

        parts = []

        for key, value in selected.items():

            parts.append(
                f"{key}: {value}"
            )

        return "\\r\\n".join(parts) + "\\r\\n"


    # =====================================================
    # PLAY NEXT
    # =====================================================

    async def play_next(
        self
    ):

        if not self.voice:

            return

        if not self.voice.is_connected():

            return

        if self.starting:

            return

        self.starting = True

        try:

            # ---------------------------------------------
            # LOOP
            # ---------------------------------------------

            if self.loop and self.current:

                song = self.current

            # ---------------------------------------------
            # QUEUE
            # ---------------------------------------------

            elif self.queue:

                song = self.queue.popleft()

                self.current = song

            # ---------------------------------------------
            # AUTOPLAY
            # ---------------------------------------------

            elif self.autoplay and self.current:

                print(
                    "[MUSIC] AUTOPLAY:"
                    f" {self.current.title}"
                )

                song = await self.resolve_song(
                    self.current.title,
                    self.current.requester
                )

                if not song:

                    self.current = None

                    return

                self.current = song

            else:

                self.current = None

                await self.stop_status_animation()

                return

            # ---------------------------------------------
            # REFRESH STREAM
            # ---------------------------------------------

            song = await self.refresh_song(
                song
            )

            self.current = song

            stream_url = (
                song.stream_url
            )

            if not stream_url:

                print(
                    "[MUSIC] NO STREAM URL"
                )

                self.current = None

                return

            # ---------------------------------------------
            # STOP OLD AUDIO
            # ---------------------------------------------

            if (
                self.voice.is_playing()
                or self.voice.is_paused()
            ):

                self.voice.stop()

            # ---------------------------------------------
            # HEADERS
            # ---------------------------------------------

            header_string = (
                self.build_headers(
                    song
                )
            )

            before_options = (
                FFMPEG_BEFORE_OPTIONS
            )

            if header_string:

                before_options += (
                    f' -headers "{header_string}"'
                )

            # ---------------------------------------------
            # FFMPEG
            # ---------------------------------------------

            source = discord.FFmpegPCMAudio(

                stream_url,

                executable=FFMPEG_PATH,

                before_options=(
                    before_options
                ),

                options=(
                    FFMPEG_OPTIONS
                )
            )

            source = (
                discord.PCMVolumeTransformer(
                    source,
                    volume=self.volume
                )
            )

            # ---------------------------------------------
            # TOKEN
            # ---------------------------------------------

            self.play_token += 1

            token = self.play_token

            self.started_at = (
                time.monotonic()
            )

            # ---------------------------------------------
            # CALLBACK
            # ---------------------------------------------

            def after_play(error):

                if error:

                    print(
                        "[MUSIC] PLAYBACK ERROR:",
                        repr(error)
                    )

                try:

                    future = (
                        asyncio.run_coroutine_threadsafe(
                            self.finished(token),
                            self.bot.loop
                        )
                    )

                    future.add_done_callback(
                        lambda f: (
                            f.exception()
                            if not f.cancelled()
                            else None
                        )
                    )

                except Exception as e:

                    print(
                        "[MUSIC] CALLBACK ERROR:",
                        repr(e)
                    )

            # ---------------------------------------------
            # PLAY IMMEDIATELY
            # ---------------------------------------------

            self.voice.play(
                source,
                after=after_play
            )

            print(
                "[MUSIC] NOW PLAYING:",
                song.title
            )

            print(
                "[MUSIC] DURATION:",
                format_duration(
                    song.duration
                )
            )

            # ---------------------------------------------
            # CHANNEL STATUS
            # ---------------------------------------------

            await self.start_status_animation(
                song
            )

            # ---------------------------------------------
            # NOW PLAYING MESSAGE
            # ---------------------------------------------

            await self.send_now_playing()

        except Exception as e:

            print(
                "[MUSIC] PLAY ERROR:",
                repr(e)
            )

        finally:

            self.starting = False


    # =====================================================
    # FINISHED
    # =====================================================

    async def finished(
        self,
        token
    ):

        if token != self.play_token:

            return

        await self.play_next()


    # =====================================================
    # NOW PLAYING
    # =====================================================

    async def send_now_playing(
        self
    ):

        if not self.text_channel:

            return

        if not self.current:

            return

        song = self.current

        embed = discord.Embed(

            title="🎵 HSL-CORP MUSIC",

            description=(

                "## 🎶 NOW PLAYING\n\n"

                f"**[{song.title}]"
                f"({song.url})**\n\n"

                "━━━━━━━━━━━━━━━━━━━━\n"

                f"⏱️ **Duration:** "
                f"`{format_duration(song.duration)}`\n"

                f"👤 **Requested by:** "
                f"{song.requester.mention}\n"

                f"🔊 **Volume:** "
                f"`{int(self.volume * 100)}%`\n"

                f"🔁 **Loop:** "
                f"{'🟢 ON' if self.loop else '🔴 OFF'}\n"

                f"🤖 **Autoplay:** "
                f"{'🟢 ON' if self.autoplay else '🔴 OFF'}\n"

                "━━━━━━━━━━━━━━━━━━━━"
            ),

            color=discord.Color.blurple()
        )

        if song.thumbnail:

            embed.set_image(
                url=song.thumbnail
            )

        embed.set_thumbnail(
            url=HSL_GIF
        )

        embed.set_footer(
            text=(
                "HSL-CORP • Fast Music System"
            )
        )

        view = MusicControlView(
            self
        )

        try:

            # IMPORTANT:
            # Delete previous NOW PLAYING message
            # so only current song remains.

            if self.now_playing_message:

                try:

                    await self.now_playing_message.delete()

                except Exception:

                    pass

                self.now_playing_message = None

            # IMPORTANT:
            # This sends directly into the Voice Channel
            # text chat.

            self.now_playing_message = (
                await self.text_channel.send(
                    embed=embed,
                    view=view
                )
            )

        except Exception as e:

            print(
                "[MUSIC] NOW PLAYING ERROR:",
                repr(e)
            )


# =========================================================
# MUSIC CONTROL VIEW
# =========================================================

class MusicControlView(
    discord.ui.View
):

    def __init__(
        self,
        player
    ):

        super().__init__(
            timeout=None
        )

        self.player = player


    # =====================================================
    # PAUSE / RESUME
    # =====================================================

    @discord.ui.button(
        label="Pause",
        emoji="⏯️",
        style=discord.ButtonStyle.primary
    )
    async def pause_resume(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        voice = self.player.voice

        if not voice:

            return await interaction.response.send_message(
                "❌ Music is not playing.",
                ephemeral=True
            )

        if voice.is_playing():

            voice.pause()

            button.label = "Resume"

            await interaction.response.edit_message(
                view=self
            )

            return

        if voice.is_paused():

            voice.resume()

            button.label = "Pause"

            await interaction.response.edit_message(
                view=self
            )

            return

        await interaction.response.send_message(
            "❌ Music is not playing.",
            ephemeral=True
        )


    # =====================================================
    # SKIP
    # =====================================================

    @discord.ui.button(
        label="Skip",
        emoji="⏭️",
        style=discord.ButtonStyle.success
    )
    async def skip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not self.player.voice:

            return await interaction.response.send_message(
                "❌ Music is not playing.",
                ephemeral=True
            )

        await interaction.response.defer()

        self.player.play_token += 1

        if (
            self.player.voice.is_playing()
            or self.player.voice.is_paused()
        ):

            self.player.voice.stop()

        self.player.starting = False

        self.player.current = None

        await self.player.play_next()


    # =====================================================
    # LOOP
    # =====================================================

    @discord.ui.button(
        label="Loop",
        emoji="🔁",
        style=discord.ButtonStyle.secondary
    )
    async def loop(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.player.loop = (
            not self.player.loop
        )

        status = (
            "🟢 ON"
            if self.player.loop
            else "🔴 OFF"
        )

        await interaction.response.send_message(
            f"🔁 Loop: **{status}**",
            ephemeral=True
        )

        await self.player.send_now_playing()


    # =====================================================
    # AUTOPLAY
    # =====================================================

    @discord.ui.button(
        label="Autoplay",
        emoji="🤖",
        style=discord.ButtonStyle.secondary
    )
    async def autoplay(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.player.autoplay = (
            not self.player.autoplay
        )

        status = (
            "🟢 ON"
            if self.player.autoplay
            else "🔴 OFF"
        )

        await interaction.response.send_message(
            f"🤖 Autoplay: **{status}**",
            ephemeral=True
        )

        await self.player.send_now_playing()


    # =====================================================
    # STOP
    # =====================================================

    @discord.ui.button(
        label="Stop",
        emoji="⏹️",
        style=discord.ButtonStyle.danger
    )
    async def stop(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer()

        self.player.play_token += 1

        self.player.queue.clear()

        self.player.current = None

        self.player.starting = False

        await self.player.stop_status_animation()

        if self.player.voice:

            if (
                self.player.voice.is_playing()
                or self.player.voice.is_paused()
            ):

                self.player.voice.stop()

            try:

                await self.player.voice.disconnect()

            except Exception:

                pass

        self.player.voice = None

        self.player.voice_channel = None

        self.player.text_channel = None

        self.player.started_at = None

        self.player.now_playing_message = None

        try:

            await interaction.message.edit(

                content=(
                    "⏹️ **Music stopped "
                    "& queue cleared.**"
                ),

                embed=None,

                view=None
            )

        except Exception:

            pass


# =========================================================
# MUSIC COG
# =========================================================

class Music(
    commands.Cog
):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

        self.players = {}


    # =====================================================
    # GET PLAYER
    # =====================================================

    def get_player(
        self,
        guild_id
    ):

        if guild_id not in self.players:

            self.players[guild_id] = (
                MusicPlayer(
                    self.bot
                )
            )

        return self.players[
            guild_id
        ]


    # =====================================================
    # PLAY
    # =====================================================

    @commands.hybrid_command(
        name="play",
        description="Play a YouTube song"
    )
    async def play(
        self,
        ctx,
        *,
        query: str
    ):

        if not ctx.guild:

            return await ctx.send(
                "❌ This command can only be "
                "used in a server.",
                delete_after=4
            )

        if not ctx.author.voice:

            return await ctx.send(
                "❌ Please join a voice channel first.",
                delete_after=4
            )

        voice_channel = (
            ctx.author.voice.channel
        )

        # -------------------------------------------------
        # HYBRID COMMAND ACK
        # -------------------------------------------------

        # Slash command ko acknowledge karte hain,
        # lekin baad mein original response delete kar denge
        # taaki normal text channel mein message na rahe.

        interaction_deferred = False

        if ctx.interaction:

            try:

                await ctx.defer()

                interaction_deferred = True

            except Exception as e:

                print(
                    "[MUSIC] DEFER ERROR:",
                    repr(e)
                )

        player = self.get_player(
            ctx.guild.id
        )

        # -------------------------------------------------
        # IMPORTANT:
        # MUSIC MESSAGE CHANNEL = VOICE CHANNEL
        # -------------------------------------------------

        player.text_channel = (
            voice_channel
        )

        player.voice_channel = (
            voice_channel
        )

        # -------------------------------------------------
        # CONNECT + RESOLVE IN PARALLEL
        # -------------------------------------------------

        connect_task = asyncio.create_task(
            player.connect_to(
                voice_channel
            )
        )

        song_task = asyncio.create_task(
            player.resolve_song(
                query,
                ctx.author
            )
        )

        connected, song = await asyncio.gather(
            connect_task,
            song_task
        )

        if not connected:

            if interaction_deferred:

                try:

                    await ctx.interaction.delete_original_response()

                except Exception:

                    pass

            return await voice_channel.send(
                "❌ Failed to connect to voice channel."
            )

        if not song:

            if interaction_deferred:

                try:

                    await ctx.interaction.delete_original_response()

                except Exception:

                    pass

            return await voice_channel.send(
                "❌ **Song not found.**\n"
                "YouTube request failed."
            )

        # -------------------------------------------------
        # DELETE SLASH COMMAND THINKING
        # -------------------------------------------------

        if interaction_deferred:

            try:

                await ctx.interaction.delete_original_response()

            except Exception:

                pass

        # -------------------------------------------------
        # CHECK PLAYING
        # -------------------------------------------------

        was_playing = (

            player.starting

            or (
                player.voice
                and (
                    player.voice.is_playing()
                    or player.voice.is_paused()
                )
            )

            or player.current is not None
        )

        # -------------------------------------------------
        # QUEUE
        # -------------------------------------------------

        player.queue.append(
            song
        )

        print(
            "[MUSIC] QUEUED:",
            song.title,
            format_duration(
                song.duration
            )
        )

        # -------------------------------------------------
        # IF ALREADY PLAYING
        # -------------------------------------------------

        if was_playing:

            position = len(
                player.queue
            )

            embed = discord.Embed(

                title="🎵 ADDED TO QUEUE",

                description=(

                    f"**[{song.title}]"
                    f"({song.url})**\n\n"

                    f"⏱️ **Duration:** "
                    f"`{format_duration(song.duration)}`\n"

                    f"👤 **Requested by:** "
                    f"{ctx.author.mention}\n"

                    f"📍 **Position:** "
                    f"`{position}`"
                ),

                color=discord.Color.green()
            )

            if song.thumbnail:

                embed.set_thumbnail(
                    url=song.thumbnail
                )

            # IMPORTANT:
            # Queue message also goes into Voice Channel.

            await voice_channel.send(
                embed=embed,
                delete_after=8
            )

            return

        # -------------------------------------------------
        # START MUSIC
        # -------------------------------------------------

        await player.play_next()


    # =====================================================
    # SKIP
    # =====================================================

    @commands.hybrid_command(
        name="skip",
        description="Skip current song"
    )
    async def skip(
        self,
        ctx
    ):

        if not ctx.guild:

            return

        player = self.get_player(
            ctx.guild.id
        )

        if not player.voice:

            return await ctx.send(
                "❌ Music is not playing.",
                delete_after=4
            )

        player.play_token += 1

        if (
            player.voice.is_playing()
            or player.voice.is_paused()
        ):

            player.voice.stop()

        player.current = None

        player.starting = False

        await player.play_next()


    # =====================================================
    # PAUSE
    # =====================================================

    @commands.hybrid_command(
        name="pause",
        description="Pause music"
    )
    async def pause(
        self,
        ctx
    ):

        if not ctx.guild:

            return

        player = self.get_player(
            ctx.guild.id
        )

        if (
            player.voice
            and player.voice.is_playing()
        ):

            player.voice.pause()

            return await player.text_channel.send(
                "⏸️ **Music paused.**",
                delete_after=3
            )

        await player.text_channel.send(
            "❌ Music is not playing.",
            delete_after=3
        )


    # =====================================================
    # RESUME
    # =====================================================

    @commands.hybrid_command(
        name="resume",
        description="Resume music"
    )
    async def resume(
        self,
        ctx
    ):

        if not ctx.guild:

            return

        player = self.get_player(
            ctx.guild.id
        )

        if (
            player.voice
            and player.voice.is_paused()
        ):

            player.voice.resume()

            return await player.text_channel.send(
                "▶️ **Music resumed.**",
                delete_after=3
            )

        await player.text_channel.send(
            "❌ Music is not paused.",
            delete_after=3
        )


    # =====================================================
    # STOP
    # =====================================================

    @commands.hybrid_command(
        name="stop",
        description="Stop music"
    )
    async def stop(
        self,
        ctx
    ):

        if not ctx.guild:

            return

        player = self.get_player(
            ctx.guild.id
        )

        player.play_token += 1

        player.queue.clear()

        player.current = None

        player.starting = False

        await player.stop_status_animation()

        if player.voice:

            if (
                player.voice.is_playing()
                or player.voice.is_paused()
            ):

                player.voice.stop()

            try:

                await player.voice.disconnect()

            except Exception:

                pass

        channel = (
            player.text_channel
        )

        player.voice = None

        player.voice_channel = None

        player.text_channel = None

        player.started_at = None

        player.now_playing_message = None

        if channel:

            await channel.send(
                "⏹️ **Music stopped & "
                "queue cleared.**",
                delete_after=4
            )


    # =====================================================
    # QUEUE
    # =====================================================

    @commands.hybrid_command(
        name="queue",
        description="Show music queue"
    )
    async def queue(
        self,
        ctx
    ):

        if not ctx.guild:

            return

        player = self.get_player(
            ctx.guild.id
        )

        channel = (
            player.text_channel
            or (
                ctx.author.voice.channel
                if ctx.author.voice
                else ctx.channel
            )
        )

        if not player.queue:

            return await channel.send(
                "📭 **Queue is empty.**",
                delete_after=4
            )

        lines = []

        for index, song in enumerate(
            list(player.queue)[:MAX_QUEUE_DISPLAY],
            1
        ):

            lines.append(

                f"`{index}.` "
                f"**{song.title[:65]}** "
                f"`{format_duration(song.duration)}`"
            )

        embed = discord.Embed(

            title="📜 HSL-CORP MUSIC QUEUE",

            description="\n".join(
                lines
            ),

            color=discord.Color.blurple()
        )

        if player.current:

            embed.add_field(

                name="🎵 Currently Playing",

                value=(

                    f"**{player.current.title}**\n"

                    f"⏱️ "
                    f"`{format_duration(player.current.duration)}`"
                ),

                inline=False
            )

        embed.set_thumbnail(
            url=HSL_GIF
        )

        await channel.send(
            embed=embed
        )


    # =====================================================
    # NOW PLAYING
    # =====================================================

    @commands.hybrid_command(
        name="nowplaying",
        description="Show current song"
    )
    async def nowplaying(
        self,
        ctx
    ):

        if not ctx.guild:

            return

        player = self.get_player(
            ctx.guild.id
        )

        channel = (
            player.text_channel
            or (
                ctx.author.voice.channel
                if ctx.author.voice
                else ctx.channel
            )
        )

        if not player.current:

            return await channel.send(
                "📭 **Nothing is playing.**",
                delete_after=4
            )

        song = player.current

        embed = discord.Embed(

            title="🎵 NOW PLAYING",

            description=(

                f"**[{song.title}]"
                f"({song.url})**\n\n"

                f"⏱️ **Duration:** "
                f"`{format_duration(song.duration)}`\n"

                f"👤 **Requested by:** "
                f"{song.requester.mention}\n"

                f"🔊 **Volume:** "
                f"`{int(player.volume * 100)}%`"
            ),

            color=discord.Color.blurple()
        )

        if song.thumbnail:

            embed.set_image(
                url=song.thumbnail
            )

        embed.set_thumbnail(
            url=HSL_GIF
        )

        await channel.send(
            embed=embed
        )


# =========================================================
# SETUP
# =========================================================

async def setup(
    bot
):

    await bot.add_cog(
        Music(bot)
    )

    print(
        "🎵 HSL-CORP FAST MUSIC SYSTEM LOADED"
    )