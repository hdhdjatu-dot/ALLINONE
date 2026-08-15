import asyncio
import os
import shutil
import ctypes
import ctypes.util
import time
from collections import deque

import aiohttp
import discord
from discord.ext import commands
import yt_dlp


# =========================================================
# HSL-CORP ULTRA MUSIC SYSTEM - FAST VERSION
# =========================================================


# =========================================================
# OPUS
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
            print(f"[MUSIC] [WARN] Opus failed {path}: {e}")

    print("[MUSIC] [ERROR] Opus codec NOT loaded.")
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
        f"[MUSIC] [COOKIE] Local cookies found: "
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
            f.write(YOUTUBE_COOKIES)

        print(
            "[MUSIC] [COOKIE] Cookies loaded from ENV."
        )

    except Exception as e:

        print(
            f"[MUSIC] [ERROR] Cookie error: {e!r}"
        )

else:

    print(
        "[MUSIC] [WARN] YouTube cookies not found."
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
# FFMPEG
# =========================================================

def find_ffmpeg():

    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg:
        print(f"[MUSIC] [OK] FFmpeg found: {ffmpeg}")
        return ffmpeg

    paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]

    for path in paths:

        if os.path.isfile(path):

            print(
                f"[MUSIC] [OK] FFmpeg found: {path}"
            )

            return path

    print(
        "[MUSIC] [WARN] FFmpeg not found. "
        "Using ffmpeg."
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

    "source_address": "0.0.0.0",

    # YouTube JS challenge
    "js_runtimes": {
        "node": {}
    },

    "remote_components": [
        "ejs:github"
    ],

    "http_headers": {

        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 "
            "Safari/537.36"
        ),

        "Accept-Language":
            "en-US,en;q=0.9",
    },

    "socket_timeout": 15,

    "retries": 2,

    "fragment_retries": 2,

    "concurrent_fragment_downloads": 1,

    "ignoreerrors": False,
}


# =========================================================
# SONG
# =========================================================

class Song:

    def __init__(
        self,
        title,
        url,
        thumbnail,
        requester
    ):

        self.title = title
        self.url = url
        self.thumbnail = thumbnail
        self.requester = requester

        # Cached direct stream.
        # This is the important speed optimization.
        self.stream_url = None


# =========================================================
# MUSIC PLAYER
# =========================================================

class MusicPlayer:

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

        # Playback generation
        self.play_token = 0

        # Prevent duplicate play_next
        self.play_lock = asyncio.Lock()

        # Prevent duplicate skip
        self.skip_lock = asyncio.Lock()

        self.now_playing_message = None

        self.last_play_request = None
        self.last_play_request_time = 0.0

        self.autoplay_history = deque(
            maxlen=30
        )

        self.play_history = deque(
            maxlen=30
        )

        self.last_manual_query = None


    # =====================================================
    # INVALIDATE
    # =====================================================

    def invalidate_playback(self):

        self.play_token += 1

        print(
            f"[MUSIC] [TOKEN] Invalidated -> "
            f"{self.play_token}"
        )

        return self.play_token


    # =====================================================
    # OPTIONS
    # =====================================================

    def get_ytdlp_options(
        self,
        use_cookies=True
    ):

        options = dict(
            YTDLP_OPTIONS
        )

        options["http_headers"] = dict(
            YTDLP_OPTIONS["http_headers"]
        )

        if (
            use_cookies
            and COOKIE_FILE
            and os.path.isfile(COOKIE_FILE)
        ):

            options["cookiefile"] = COOKIE_FILE

        return options


    # =====================================================
    # VOICE STATUS
    # =====================================================

    async def update_voice_status(
        self,
        text
    ):

        if (
            not self.voice
            or not self.voice.is_connected()
            or not self.voice.channel
        ):
            return

        channel_id = self.voice.channel.id

        url = (
            f"https://discord.com/api/v10/"
            f"channels/{channel_id}/voice-status"
        )

        headers = {
            "Authorization":
                f"Bot {self.bot.http.token}",
            "Content-Type":
                "application/json",
        }

        try:

            async with aiohttp.ClientSession() as session:

                async with session.put(
                    url,
                    headers=headers,
                    json={
                        "status": str(text)[:500]
                    }
                ) as response:

                    if response.status not in (
                        200,
                        204
                    ):

                        error = await response.text()

                        print(
                            "[MUSIC] [WARN] "
                            f"Voice status {response.status}: "
                            f"{error}"
                        )

        except Exception as e:

            print(
                "[MUSIC] [WARN] Voice status:",
                repr(e)
            )


    async def clear_voice_status(self):

        if (
            not self.voice
            or not self.voice.channel
        ):
            return

        channel_id = self.voice.channel.id

        url = (
            f"https://discord.com/api/v10/"
            f"channels/{channel_id}/voice-status"
        )

        headers = {
            "Authorization":
                f"Bot {self.bot.http.token}",
            "Content-Type":
                "application/json",
        }

        try:

            async with aiohttp.ClientSession() as session:

                await session.put(
                    url,
                    headers=headers,
                    json={
                        "status": ""
                    }
                )

        except Exception:
            pass


    # =====================================================
    # RESOLVE SONG
    # =====================================================

    async def resolve_song(
        self,
        search_query,
        requester
    ):

        loop = asyncio.get_running_loop()

        def extract():

            query = str(
                search_query
            ).strip()

            if not query:
                return None

            options = self.get_ytdlp_options(
                use_cookies=bool(COOKIE_FILE)
            )

            options["skip_download"] = True

            if query.startswith(
                (
                    "http://",
                    "https://"
                )
            ):

                target = query

                print(
                    "[MUSIC] [URL] Direct URL"
                )

            else:

                target = (
                    f"ytsearch1:{query}"
                )

                print(
                    "[MUSIC] [SEARCH]",
                    query
                )

            try:

                with yt_dlp.YoutubeDL(
                    options
                ) as ydl:

                    info = ydl.extract_info(
                        target,
                        download=False
                    )

                if not info:
                    return None

                if "entries" in info:

                    entries = [
                        e
                        for e in (
                            info.get("entries")
                            or []
                        )
                        if e
                    ]

                    if not entries:
                        return None

                    info = entries[0]

                webpage_url = (
                    info.get("webpage_url")
                    or info.get("original_url")
                )

                video_id = info.get("id")

                if (
                    not webpage_url
                    and video_id
                ):

                    webpage_url = (
                        "https://www.youtube.com/watch?v="
                        + video_id
                    )

                if not webpage_url:
                    return None

                return {
                    "title":
                        info.get(
                            "title",
                            "Unknown Song"
                        ),

                    "url":
                        webpage_url,

                    "thumbnail":
                        info.get(
                            "thumbnail"
                        ),

                    # If yt-dlp already gave us a URL,
                    # cache it immediately.
                    "stream_url":
                        info.get("url"),
                }

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] Resolve:",
                    repr(e)
                )

                return None

        try:

            data = await loop.run_in_executor(
                None,
                extract
            )

        except Exception as e:

            print(
                "[MUSIC] [ERROR] Resolve executor:",
                repr(e)
            )

            return None

        if not data:
            return None

        song = Song(
            data["title"],
            data["url"],
            data.get("thumbnail"),
            requester
        )

        # Cache only if available.
        song.stream_url = data.get(
            "stream_url"
        )

        print(
            "[MUSIC] [OK] Selected:",
            song.title
        )

        return song


    # =====================================================
    # FRESH AUDIO STREAM
    # =====================================================

    async def get_audio_stream(
        self,
        song
    ):

        # -------------------------------------------------
        # USE CACHED STREAM FIRST
        # -------------------------------------------------

        if song.stream_url:

            print(
                "[MUSIC] [FAST] Using cached stream."
            )

            return song.stream_url

        loop = asyncio.get_running_loop()

        def extract():

            try:

                options = self.get_ytdlp_options(
                    use_cookies=bool(COOKIE_FILE)
                )

                options.update({

                    "skip_download": True,

                    "format":
                        "bestaudio[ext=webm]/"
                        "bestaudio[ext=m4a]/"
                        "bestaudio/best",

                    "noplaylist": True,

                })

                with yt_dlp.YoutubeDL(
                    options
                ) as ydl:

                    info = ydl.extract_info(
                        song.url,
                        download=False
                    )

                if not info:
                    return None

                if "entries" in info:

                    entries = [
                        e
                        for e in (
                            info.get("entries")
                            or []
                        )
                        if e
                    ]

                    if not entries:
                        return None

                    info = entries[0]

                return info.get(
                    "url"
                )

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] Stream extraction:",
                    repr(e)
                )

                return None

        try:

            stream = await loop.run_in_executor(
                None,
                extract
            )

            if stream:

                song.stream_url = stream

                print(
                    "[MUSIC] [OK] Fresh stream obtained."
                )

            return stream

        except Exception as e:

            print(
                "[MUSIC] [ERROR] Audio:",
                repr(e)
            )

            return None


    # =====================================================
    # AUTOPLAY
    # =====================================================

    async def resolve_autoplay_song(
        self
    ):

        if not self.current:
            return None

        requester = (
            self.current.requester
        )

        previous_url = (
            self.current.url
        )

        query = (
            self.current.title
        )

        loop = asyncio.get_running_loop()

        history = set(
            self.autoplay_history
        )

        def extract():

            options = self.get_ytdlp_options(
                use_cookies=bool(COOKIE_FILE)
            )

            options["skip_download"] = True
            options["extract_flat"] = True

            try:

                with yt_dlp.YoutubeDL(
                    options
                ) as ydl:

                    info = ydl.extract_info(
                        f"ytsearch5:{query}",
                        download=False
                    )

                if not info:
                    return None

                for entry in (
                    info.get("entries")
                    or []
                ):

                    if not entry:
                        continue

                    title = (
                        entry.get(
                            "title",
                            ""
                        )
                        .strip()
                    )

                    video_id = entry.get(
                        "id"
                    )

                    url = (
                        entry.get(
                            "webpage_url"
                        )
                        or entry.get(
                            "original_url"
                        )
                    )

                    if (
                        not url
                        and video_id
                    ):

                        url = (
                            "https://www.youtube.com/watch?v="
                            + video_id
                        )

                    if not url:
                        continue

                    if url == previous_url:
                        continue

                    if url in history:
                        continue

                    return {
                        "title": title,
                        "url": url,
                        "thumbnail":
                            entry.get(
                                "thumbnail"
                            ),
                    }

            except Exception as e:

                print(
                    "[MUSIC] [WARN] Autoplay:",
                    repr(e)
                )

            return None

        try:

            data = await loop.run_in_executor(
                None,
                extract
            )

        except Exception as e:

            print(
                "[MUSIC] [ERROR] Autoplay:",
                repr(e)
            )

            return None

        if not data:
            return None

        song = Song(
            data["title"],
            data["url"],
            data.get("thumbnail"),
            requester
        )

        self.autoplay_history.append(
            song.url
        )

        return song


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

        async with self.play_lock:

            if self.starting:
                return

            self.starting = True

            try:

                # -----------------------------------------
                # SELECT SONG
                # -----------------------------------------

                if (
                    self.loop
                    and self.current
                ):

                    song = self.current

                elif self.queue:

                    song = (
                        self.queue.popleft()
                    )

                    self.current = song

                elif (
                    self.autoplay
                    and self.current
                ):

                    print(
                        "[MUSIC] [AUTOPLAY] Searching..."
                    )

                    song = (
                        await
                        self.resolve_autoplay_song()
                    )

                    if not song:

                        self.current = None

                        await self.clear_voice_status()

                        return

                    self.current = song

                else:

                    self.current = None

                    await self.clear_voice_status()

                    return

                # -----------------------------------------
                # NEW TOKEN
                # -----------------------------------------

                self.play_token += 1

                token = self.play_token

                print(
                    "[MUSIC] [PREPARE]",
                    song.title,
                    "| token:",
                    token
                )

                # -----------------------------------------
                # GET STREAM
                # -----------------------------------------

                stream_url = (
                    await
                    self.get_audio_stream(
                        song
                    )
                )

                if token != self.play_token:

                    print(
                        "[MUSIC] [CANCELLED] Old token."
                    )

                    return

                if not stream_url:

                    print(
                        "[MUSIC] [ERROR] "
                        "No stream:",
                        song.title
                    )

                    # Try next queued song.
                    if self.queue:

                        self.current = None

                        self.starting = False

                        await self.play_next()

                        return

                    # Try autoplay.
                    if self.autoplay:

                        self.starting = False

                        await self.play_next()

                        return

                    self.current = None

                    return

                # -----------------------------------------
                # STOP OLD AUDIO
                # -----------------------------------------

                if (
                    self.voice.is_playing()
                    or self.voice.is_paused()
                ):

                    self.voice.stop()

                    # VERY SMALL WAIT ONLY
                    await asyncio.sleep(
                        0.03
                    )

                # -----------------------------------------
                # FFMPEG
                # -----------------------------------------

                before_options = (
                    "-reconnect 1 "
                    "-reconnect_streamed 1 "
                    "-reconnect_at_eof 1 "
                    "-reconnect_on_network_error 1 "
                    "-reconnect_on_http_error "
                    "403,404,429,500,502,503,504 "
                    "-reconnect_delay_max 2 "
                    "-nostdin"
                )

                ffmpeg_options = (
                    "-vn "
                    "-loglevel error "
                    "-ar 48000 "
                    "-ac 2 "
                    "-bufsize 512k"
                )

                source = discord.FFmpegPCMAudio(
                    stream_url,
                    executable=FFMPEG_PATH,
                    before_options=before_options,
                    options=ffmpeg_options
                )

                source = (
                    discord.PCMVolumeTransformer(
                        source,
                        volume=self.volume
                    )
                )

                # -----------------------------------------
                # CALLBACK
                # -----------------------------------------

                def after_play(error):

                    if error:

                        print(
                            "[MUSIC] [FFMPEG ERROR]",
                            repr(error)
                        )

                    try:

                        asyncio.run_coroutine_threadsafe(
                            self.finished(token),
                            self.bot.loop
                        )

                    except Exception as e:

                        print(
                            "[MUSIC] [CALLBACK ERROR]",
                            repr(e)
                        )

                # -----------------------------------------
                # FINAL TOKEN CHECK
                # -----------------------------------------

                if token != self.play_token:

                    try:
                        source.cleanup()
                    except Exception:
                        pass

                    return

                # -----------------------------------------
                # START AUDIO
                # -----------------------------------------

                try:

                    self.voice.play(
                        source,
                        after=after_play
                    )

                except Exception as e:

                    print(
                        "[MUSIC] [ERROR] voice.play:",
                        repr(e)
                    )

                    try:
                        source.cleanup()
                    except Exception:
                        pass

                    return

                print(
                    "[MUSIC] [PLAYING]",
                    song.title
                )

                # Don't wait for Discord API before audio.
                asyncio.create_task(
                    self.update_voice_status(
                        f"🎵 {song.title}"
                    )
                )

                asyncio.create_task(
                    self.send_now_playing()
                )

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] play_next:",
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

        if (
            not self.voice
            or not self.voice.is_connected()
        ):
            return

        # -----------------------------------------
        # NO ARTIFICIAL 0.7 SECOND DELAY
        # -----------------------------------------

        # Discord/FFmpeg callback can arrive a tiny
        # moment before is_playing() updates.
        await asyncio.sleep(
            0.05
        )

        if token != self.play_token:
            return

        if (
            self.voice.is_playing()
            or self.voice.is_paused()
        ):
            return

        print(
            "[MUSIC] [FINISHED] Next song."
        )

        await self.play_next()


    # =====================================================
    # NOW PLAYING
    # =====================================================

    async def send_now_playing(
        self
    ):

        if (
            not self.text_channel
            or not self.current
        ):
            return

        song = self.current

        embed = discord.Embed(

            title="🎵 HSL-CORP MUSIC",

            description=(
                "## 🎶 NOW PLAYING\n\n"
                f"**[{song.title}]"
                f"({song.url})**\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Requested by: "
                f"{song.requester.mention}\n"
                f"🔊 Volume: "
                f"{int(self.volume * 100)}%\n"
                f"🔁 Loop: "
                f"{'🟢 ON' if self.loop else '🔴 OFF'}\n"
                f"🤖 Autoplay: "
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
            text="HSL & CORPORATION • Music System"
        )

        view = MusicControlView(
            self
        )

        try:

            if self.now_playing_message:

                await self.now_playing_message.edit(
                    embed=embed,
                    content=None,
                    view=view
                )

            else:

                self.now_playing_message = (
                    await self.text_channel.send(
                        embed=embed,
                        view=view
                    )
                )

        except discord.NotFound:

            self.now_playing_message = None

        except Exception as e:

            print(
                "[MUSIC] [ERROR] Now playing:",
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

        elif voice.is_paused():

            voice.resume()

            button.label = "Pause"

            await interaction.response.edit_message(
                view=self
            )

        else:

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

        player = self.player

        if not player.voice:

            return await interaction.response.send_message(
                "❌ Music is not playing.",
                ephemeral=True
            )

        if player.skip_lock.locked():

            return await interaction.response.send_message(
                "⚠️ Skip already processing.",
                ephemeral=True
            )

        await interaction.response.defer(
            ephemeral=True
        )

        async with player.skip_lock:

            # Invalidate old FFmpeg callback.
            player.invalidate_playback()

            # Stop immediately.
            if (
                player.voice.is_playing()
                or player.voice.is_paused()
            ):

                player.voice.stop()

            # DO NOT set current=None.
            # It is needed for autoplay context.

            player.starting = False

            # No 0.4 second artificial delay.
            await player.play_next()

        try:

            await interaction.followup.send(
                "⏭️ Skipped.",
                ephemeral=True
            )

        except Exception:
            pass


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

        await interaction.response.defer(
            ephemeral=True
        )

        player = self.player

        player.invalidate_playback()

        player.queue.clear()

        player.current = None

        player.starting = False

        player.autoplay_history.clear()

        player.play_history.clear()

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

        player.voice = None

        player.text_channel = None

        player.now_playing_message = None

        try:

            await interaction.message.edit(
                content=(
                    "⏹️ **Music stopped & queue cleared.**"
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

        self.play_locks = {}


    # =====================================================
    # PLAYER
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
    # PLAY LOCK
    # =====================================================

    def get_play_lock(
        self,
        guild_id
    ):

        if guild_id not in self.play_locks:

            self.play_locks[guild_id] = (
                asyncio.Lock()
            )

        return self.play_locks[
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
                "❌ Server only.",
                delete_after=4
            )

        if not ctx.author.voice:

            return await ctx.send(
                "❌ Please join a voice channel first.",
                delete_after=4
            )

        player = self.get_player(
            ctx.guild.id
        )

        lock = self.get_play_lock(
            ctx.guild.id
        )

        async with lock:

            player.text_channel = ctx.channel

            voice_channel = (
                ctx.author.voice.channel
            )

            # -----------------------------------------
            # VOICE
            # -----------------------------------------

            try:

                if ctx.voice_client:

                    player.voice = (
                        ctx.voice_client
                    )

                    if (
                        player.voice.channel
                        != voice_channel
                    ):

                        await player.voice.move_to(
                            voice_channel
                        )

                else:

                    player.voice = (
                        await voice_channel.connect()
                    )

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] Voice:",
                    repr(e)
                )

                return await ctx.send(
                    "❌ Failed to connect to voice.",
                    delete_after=5
                )

            # -----------------------------------------
            # LOAD
            # -----------------------------------------

            loading = await ctx.send(
                "🔎 **Loading song...**"
            )

            song = (
                await player.resolve_song(
                    query,
                    ctx.author
                )
            )

            if not song:

                try:

                    await loading.edit(
                        content=(
                            "❌ **YouTube could not "
                            "provide this song right now.**"
                        )
                    )

                except Exception:
                    pass

                return

            try:

                await loading.delete()

            except Exception:
                pass

            # -----------------------------------------
            # PLAYING CHECK
            # -----------------------------------------

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
                or bool(player.queue)
            )

            player.queue.append(
                song
            )

            print(
                "[MUSIC] [QUEUE] Added:",
                song.title
            )

            # -----------------------------------------
            # QUEUED
            # -----------------------------------------

            if was_playing:

                position = len(
                    player.queue
                )

                embed = discord.Embed(

                    title="🎵 ADDED TO QUEUE",

                    description=(
                        f"**[{song.title}]"
                        f"({song.url})**\n\n"
                        f"👤 {ctx.author.mention}\n"
                        f"📍 Position: `{position}`"
                    ),

                    color=discord.Color.green()
                )

                if song.thumbnail:

                    embed.set_image(
                        url=song.thumbnail
                    )

                embed.set_thumbnail(
                    url=HSL_GIF
                )

                return await ctx.send(
                    embed=embed,
                    delete_after=8
                )

            # -----------------------------------------
            # START
            # -----------------------------------------

            await player.play_next()

            # NO 1 SECOND WAIT HERE.
            # Audio status is checked asynchronously.


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

            return await ctx.send(
                "❌ Server only.",
                delete_after=3
            )

        player = self.get_player(
            ctx.guild.id
        )

        if not player.voice:

            return await ctx.send(
                "❌ Music is not playing.",
                delete_after=4
            )

        if player.skip_lock.locked():

            return await ctx.send(
                "⚠️ Skip already processing.",
                delete_after=3
            )

        async with player.skip_lock:

            player.invalidate_playback()

            if (
                player.voice.is_playing()
                or player.voice.is_paused()
            ):

                player.voice.stop()

            player.starting = False

            # No artificial 0.4 sec delay.
            await player.play_next()

        # Prefix command message delete.
        try:

            await ctx.message.delete()

        except Exception:

            # Slash commands don't have a normal message.
            try:

                await ctx.send(
                    "⏭️ **Skipped.**",
                    delete_after=2
                )

            except Exception:
                pass


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

        player = self.get_player(
            ctx.guild.id
        )

        if (
            player.voice
            and player.voice.is_playing()
        ):

            player.voice.pause()

            return await ctx.send(
                "⏸️ **Music paused.**",
                delete_after=3
            )

        await ctx.send(
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

        player = self.get_player(
            ctx.guild.id
        )

        if (
            player.voice
            and player.voice.is_paused()
        ):

            player.voice.resume()

            return await ctx.send(
                "▶️ **Music resumed.**",
                delete_after=3
            )

        await ctx.send(
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

        player = self.get_player(
            ctx.guild.id
        )

        player.invalidate_playback()

        player.queue.clear()

        player.current = None

        player.starting = False

        player.autoplay_history.clear()

        player.play_history.clear()

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

        player.voice = None

        player.text_channel = None

        player.now_playing_message = None

        await ctx.send(
            "⏹️ **Music stopped & queue cleared.**",
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

        player = self.get_player(
            ctx.guild.id
        )

        if not player.queue:

            return await ctx.send(
                "📭 **Queue is empty.**",
                delete_after=4
            )

        lines = []

        for index, song in enumerate(
            list(player.queue)[:15],
            1
        ):

            lines.append(
                f"`{index}.` **{song.title[:70]}**"
            )

        embed = discord.Embed(

            title="📜 HSL-CORP MUSIC QUEUE",

            description="\n".join(
                lines
            ),

            color=discord.Color.blurple()
        )

        embed.set_thumbnail(
            url=HSL_GIF
        )

        await ctx.send(
            embed=embed
        )


    # =====================================================
    # VOLUME
    # =====================================================

    @commands.hybrid_command(
        name="volume",
        description="Change music volume"
    )
    async def volume(
        self,
        ctx,
        amount: int
    ):

        if amount < 0 or amount > 200:

            return await ctx.send(
                "❌ Volume must be between `0` and `200`.",
                delete_after=4
            )

        player = self.get_player(
            ctx.guild.id
        )

        player.volume = (
            amount / 100
        )

        if player.voice:

            source = player.voice.source

            if isinstance(
                source,
                discord.PCMVolumeTransformer
            ):

                source.volume = (
                    amount / 100
                )

        await ctx.send(
            f"🔊 **Volume set to {amount}%**",
            delete_after=4
        )


    # =====================================================
    # LOOP
    # =====================================================

    @commands.hybrid_command(
        name="loop",
        description="Toggle loop"
    )
    async def loop(
        self,
        ctx
    ):

        player = self.get_player(
            ctx.guild.id
        )

        player.loop = (
            not player.loop
        )

        status = (
            "🟢 ON"
            if player.loop
            else "🔴 OFF"
        )

        await ctx.send(
            f"🔁 **Loop: {status}**",
            delete_after=4
        )

        await player.send_now_playing()


    # =====================================================
    # AUTOPLAY
    # =====================================================

    @commands.hybrid_command(
        name="autoplay",
        description="Toggle autoplay"
    )
    async def autoplay(
        self,
        ctx
    ):

        player = self.get_player(
            ctx.guild.id
        )

        player.autoplay = (
            not player.autoplay
        )

        status = (
            "🟢 ON"
            if player.autoplay
            else "🔴 OFF"
        )

        await ctx.send(
            f"🤖 **Autoplay: {status}**",
            delete_after=4
        )

        if (
            player.autoplay
            and player.voice
            and player.current
            and not player.voice.is_playing()
            and not player.voice.is_paused()
        ):

            await player.play_next()


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

        player = self.get_player(
            ctx.guild.id
        )

        if not player.current:

            return await ctx.send(
                "❌ Nothing is playing.",
                delete_after=4
            )

        await player.send_now_playing()


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
        "[MUSIC] [OK] "
        "Music cog loaded successfully."
    )