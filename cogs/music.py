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
# OPUS
# =========================================================

def load_opus():
    if discord.opus.is_loaded():
        print("[MUSIC] ✅ Opus already loaded.")
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
                print(f"[MUSIC] ✅ Opus loaded: {path}")
                return True

        except Exception as e:
            print(f"[MUSIC] ❌ Failed to load Opus {path}: {e}")

    print("[MUSIC] ❌ Opus codec NOT loaded.")
    return False


OPUS_LOADED = load_opus()

if not OPUS_LOADED:
    print(
        "[MUSIC] ⚠️ Discord voice audio cannot play "
        "until Opus is available."
    )


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

YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES")

COOKIE_FILE = None

if os.path.isfile(COOKIE_PATH):

    COOKIE_FILE = COOKIE_PATH

    print(
        f"[MUSIC] 🍪 Local YouTube cookies found: "
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
            "[MUSIC] 🍪 YouTube cookies loaded "
            "from environment."
        )

    except Exception as e:
        print(
            "[MUSIC] ❌ Cookie file error:",
            repr(e)
        )

else:
    print(
        "[MUSIC] ⚠️ YouTube cookies not found."
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
        print(
            f"[MUSIC] ✅ FFmpeg found: {ffmpeg}"
        )
        return ffmpeg

    paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]

    for path in paths:

        if os.path.isfile(path):

            print(
                f"[MUSIC] ✅ FFmpeg found: {path}"
            )

            return path

    print(
        "[MUSIC] ⚠️ FFmpeg not found. "
        "Using 'ffmpeg' command."
    )

    return "ffmpeg"


FFMPEG_PATH = find_ffmpeg()


# =========================================================
# YT-DLP BASE OPTIONS
# =========================================================

YTDLP_OPTIONS = {
    "quiet": True,
    "no_warnings": False,
    "noplaylist": True,
    "source_address": "0.0.0.0",

    "js_runtimes": {
        "deno": {}
    },

    "remote_components": [
        "ejs:github"
    ],

    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    },

    # More stable networking
    "socket_timeout": 15,
    "retries": 3,
    "fragment_retries": 3,
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

        # Every playback gets a unique generation.
        # Old callbacks can never control a newer playback.
        self.play_token = 0

        self.now_playing_message = None

        self.play_lock = asyncio.Lock()

        self.last_play_request = None
        self.last_play_request_time = 0.0


    # =====================================================
    # VOICE STATUS
    # =====================================================

    async def update_voice_status(self, text):

        if not self.voice:
            return

        if not self.voice.is_connected():
            return

        if not self.voice.channel:
            return

        channel_id = self.voice.channel.id

        url = (
            f"https://discord.com/api/v10/"
            f"channels/{channel_id}/voice-status"
        )

        headers = {
            "Authorization": (
                f"Bot {self.bot.http.token}"
            ),
            "Content-Type": "application/json",
        }

        text = str(text)[:500]

        try:

            async with aiohttp.ClientSession() as session:

                async with session.put(
                    url,
                    headers=headers,
                    json={
                        "status": text
                    }
                ) as response:

                    if response.status in (200, 204):

                        print(
                            "[MUSIC] ✅ VC Status updated:",
                            text
                        )

                    else:

                        error = await response.text()

                        print(
                            "[MUSIC] ❌ VC Status failed "
                            f"({response.status}): {error}"
                        )

        except Exception as e:

            print(
                "[MUSIC] ❌ VC STATUS ERROR:",
                repr(e)
            )


    # =====================================================
    # CLEAR VOICE STATUS
    # =====================================================

    async def clear_voice_status(self):

        if not self.voice:
            return

        if not self.voice.channel:
            return

        channel_id = self.voice.channel.id

        url = (
            f"https://discord.com/api/v10/"
            f"channels/{channel_id}/voice-status"
        )

        headers = {
            "Authorization": (
                f"Bot {self.bot.http.token}"
            ),
            "Content-Type": "application/json",
        }

        try:

            async with aiohttp.ClientSession() as session:

                async with session.put(
                    url,
                    headers=headers,
                    json={
                        "status": ""
                    }
                ) as response:

                    if response.status in (200, 204):

                        print(
                            "[MUSIC] 🧹 VC Status cleared."
                        )

                    else:

                        error = await response.text()

                        print(
                            "[MUSIC] ⚠️ VC Status clear failed "
                            f"({response.status}): {error}"
                        )

        except Exception as e:

            print(
                "[MUSIC] ❌ VC STATUS CLEAR ERROR:",
                repr(e)
            )


    # =====================================================
    # YTDLP OPTIONS BUILDER
    # =====================================================

    def get_ytdlp_options(
        self,
        use_cookies=True
    ):

        options = dict(YTDLP_OPTIONS)

        options["http_headers"] = dict(
            YTDLP_OPTIONS["http_headers"]
        )

        if use_cookies and COOKIE_FILE:

            options["cookiefile"] = COOKIE_FILE

        return options


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
                    "[MUSIC] 🔎 Searching:",
                    query
                )

            else:

                print(
                    "[MUSIC] 🔗 Direct URL:",
                    target
                )

            # First try cookies.
            # If cookies are invalid, retry without them.
            attempts = []

            if COOKIE_FILE:
                attempts.append(True)

            attempts.append(False)

            last_error = None

            for use_cookies in attempts:

                try:

                    options = self.get_ytdlp_options(
                        use_cookies=use_cookies
                    )

                    options["skip_download"] = True

                    with yt_dlp.YoutubeDL(
                        options
                    ) as ydl:

                        info = ydl.extract_info(
                            target,
                            download=False
                        )

                        if not info:
                            continue

                        if "entries" in info:

                            entries = [
                                entry
                                for entry in info["entries"]
                                if entry
                            ]

                            if not entries:
                                continue

                            info = entries[0]

                        webpage_url = (
                            info.get("webpage_url")
                            or info.get("original_url")
                        )

                        if not webpage_url:

                            video_id = info.get("id")

                            if video_id:
                                webpage_url = (
                                    f"https://www.youtube.com/watch?v={video_id}"
                                )

                        if not webpage_url:
                            continue

                        return {
                            "title": info.get(
                                "title",
                                "Unknown Song"
                            ),
                            "url": webpage_url,
                            "thumbnail": info.get(
                                "thumbnail"
                            ),
                        }

                except Exception as e:

                    last_error = e

                    print(
                        "[MUSIC] ⚠️ Resolve attempt failed:",
                        repr(e)
                    )

                    continue

            if last_error:

                print(
                    "[MUSIC] ❌ All resolve attempts failed."
                )

            return None

        try:

            data = await loop.run_in_executor(
                None,
                extract
            )

        except Exception as e:

            print(
                "[MUSIC] ❌ RESOLVE ERROR:",
                repr(e)
            )

            return None

        if not data:
            return None

        print(
            "[MUSIC] ✅ Selected:",
            data["title"]
        )

        return Song(
            data["title"],
            data["url"],
            data["thumbnail"],
            requester
        )


    # =====================================================
    # GET AUDIO STREAM
    # =====================================================

    async def get_audio_stream(
        self,
        song
    ):

        loop = asyncio.get_running_loop()

        def extract():

            attempts = []

            if COOKIE_FILE:
                attempts.append(True)

            attempts.append(False)

            for use_cookies in attempts:

                try:

                    options = self.get_ytdlp_options(
                        use_cookies=use_cookies
                    )

                    options.update({
                        "skip_download": True,

                        "format": (
                            "bestaudio[ext=webm]/"
                            "bestaudio[ext=m4a]/"
                            "bestaudio/best"
                        ),

                        # Don't use a playlist.
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
                            continue

                        if "entries" in info:

                            entries = [
                                entry
                                for entry in info["entries"]
                                if entry
                            ]

                            if not entries:
                                continue

                            info = entries[0]

                        stream_url = info.get("url")

                        if stream_url:

                            print(
                                "[MUSIC] ✅ Fresh audio "
                                "stream obtained."
                            )

                            return stream_url

                except Exception as e:

                    print(
                        "[MUSIC] ⚠️ Stream attempt failed:",
                        repr(e)
                    )

                    continue

            return None

        try:

            stream = await loop.run_in_executor(
                None,
                extract
            )

            return stream

        except Exception as e:

            print(
                "[MUSIC] ❌ AUDIO ERROR:",
                repr(e)
            )

            return None


    # =====================================================
    # AUTOPLAY SEARCH
    # =====================================================

    async def resolve_autoplay_song(self):

        if not self.current:
            return None

        loop = asyncio.get_running_loop()

        previous_url = self.current.url

        previous_title = (
            self.current.title
            .lower()
            .strip()
        )

        requester = self.current.requester

        autoplay_queries = [
            "popular Hindi songs",
            "latest Hindi songs",
            "Hindi romantic songs",
            "Bollywood songs",
            "trending Hindi songs",
            "best Hindi songs",
            "Hindi songs",
            "popular Bollywood music",
        ]

        random.shuffle(
            autoplay_queries
        )

        def extract():

            options = self.get_ytdlp_options(
                use_cookies=True
            )

            options["skip_download"] = True
            options["extract_flat"] = True

            for query in autoplay_queries:

                try:

                    with yt_dlp.YoutubeDL(
                        options
                    ) as ydl:

                        info = ydl.extract_info(
                            f"ytsearch10:{query}",
                            download=False
                        )

                    if not info:
                        continue

                    entries = (
                        info.get("entries")
                        or []
                    )

                    valid = []

                    for entry in entries:

                        if not entry:
                            continue

                        title = (
                            entry.get(
                                "title",
                                ""
                            )
                            .strip()
                        )

                        url = (
                            entry.get(
                                "webpage_url"
                            )
                            or entry.get(
                                "original_url"
                            )
                        )

                        video_id = entry.get("id")

                        if not url and video_id:

                            url = (
                                "https://www.youtube.com/watch?v="
                                + video_id
                            )

                        if not url:
                            continue

                        if url == previous_url:
                            continue

                        if (
                            title.lower()
                            == previous_title
                        ):
                            continue

                        if (
                            "youtube.com" not in url
                            and
                            "youtu.be" not in url
                        ):
                            continue

                        valid.append(entry)

                    if valid:

                        entry = random.choice(
                            valid
                        )

                        url = (
                            entry.get(
                                "webpage_url"
                            )
                            or entry.get(
                                "original_url"
                            )
                        )

                        video_id = entry.get("id")

                        if not url and video_id:

                            url = (
                                "https://www.youtube.com/watch?v="
                                + video_id
                            )

                        return {
                            "title": entry.get(
                                "title",
                                "Unknown Song"
                            ),
                            "url": url,
                            "thumbnail": entry.get(
                                "thumbnail"
                            ),
                        }

                except Exception as e:

                    print(
                        "[MUSIC] ⚠️ Autoplay search failed:",
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
                "[MUSIC] ❌ AUTOPLAY SEARCH ERROR:",
                repr(e)
            )

            return None

        if not data:
            return None

        print(
            "[MUSIC] 🤖 Autoplay selected:",
            data["title"]
        )

        return Song(
            data["title"],
            data["url"],
            data.get("thumbnail"),
            requester
        )


    # =====================================================
    # PLAY NEXT
    # =====================================================

    async def play_next(self):

        async with self.play_lock:

            if not self.voice:
                return

            if not self.voice.is_connected():
                return

            if self.starting:
                return

            self.starting = True

            try:

                # =========================================
                # SELECT NEXT SONG
                # =========================================

                if self.loop and self.current:

                    song = self.current

                elif self.queue:

                    song = self.queue.popleft()

                    self.current = song

                elif (
                    self.autoplay
                    and self.current
                ):

                    print(
                        "[MUSIC] 🤖 Autoplay searching..."
                    )

                    song = (
                        await self.resolve_autoplay_song()
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


                print(
                    "[MUSIC] 🎵 Preparing:",
                    song.title
                )


                # =========================================
                # INVALIDATE OLD PLAYBACK
                # =========================================

                self.play_token += 1

                token = self.play_token


                # =========================================
                # STOP OLD SOURCE
                # =========================================

                if self.voice.is_playing() or self.voice.is_paused():

                    self.voice.stop()

                    await asyncio.sleep(0.15)


                # =========================================
                # GET COMPLETELY FRESH STREAM
                # =========================================

                stream_url = (
                    await self.get_audio_stream(
                        song
                    )
                )

                if not stream_url:

                    print(
                        "[MUSIC] ❌ Stream unavailable:",
                        song.title
                    )

                    # Try a different autoplay song
                    # instead of getting stuck.
                    if self.autoplay:

                        retry_song = (
                            await self.resolve_autoplay_song()
                        )

                        if retry_song:

                            self.current = retry_song

                            song = retry_song

                            stream_url = (
                                await self.get_audio_stream(
                                    song
                                )
                            )

                    if not stream_url:

                        self.current = None

                        await self.clear_voice_status()

                        return


                # =========================================
                # FFMPEG
                # =========================================

                before_options = (
                    "-reconnect 1 "
                    "-reconnect_streamed 1 "
                    "-reconnect_at_eof 1 "
                    "-reconnect_delay_max 5 "
                    "-nostdin"
                )

                ffmpeg_options = (
                    "-vn "
                    "-loglevel warning"
                )


                source = discord.FFmpegPCMAudio(
                    stream_url,
                    executable=FFMPEG_PATH,
                    before_options=before_options,
                    options=ffmpeg_options
                )


                source = discord.PCMVolumeTransformer(
                    source,
                    volume=self.volume
                )


                # =========================================
                # CALLBACK
                # =========================================

                def after_play(error):

                    if error:

                        print(
                            "[MUSIC] ❌ Playback error:",
                            repr(error)
                        )

                    try:

                        asyncio.run_coroutine_threadsafe(
                            self.finished(token),
                            self.bot.loop
                        )

                    except Exception as e:

                        print(
                            "[MUSIC] ❌ Finish callback:",
                            repr(e)
                        )


                # =========================================
                # FINAL SAFETY CHECK
                # =========================================

                if token != self.play_token:

                    print(
                        "[MUSIC] ⚠️ Old playback cancelled."
                    )

                    return


                # =========================================
                # PLAY
                # =========================================

                self.voice.play(
                    source,
                    after=after_play
                )


                print(
                    "[MUSIC] ▶️ NOW PLAYING:",
                    song.title
                )


                # =========================================
                # STATUS
                # =========================================

                await self.update_voice_status(
                    f"🎵 {song.title}"
                )


                # =========================================
                # NOW PLAYING
                # =========================================

                await self.send_now_playing()


            except Exception as e:

                print(
                    "[MUSIC] ❌ PLAYBACK ERROR:",
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

        # Old callback = ignore completely.
        if token != self.play_token:
            return

        await asyncio.sleep(0.8)

        if token != self.play_token:
            return

        if not self.voice:
            return

        if not self.voice.is_connected():
            return

        # If another source is already playing,
        # never start another one.
        if self.voice.is_playing() or self.voice.is_paused():
            return

        await self.play_next()


    # =====================================================
    # NOW PLAYING
    # =====================================================

    async def send_now_playing(self):

        if not self.text_channel:
            return

        if not self.current:
            return

        song = self.current

        embed = discord.Embed(
            title="🎵 HSL-CORP MUSIC",
            description=(
                "## 🎶 NOW PLAYING\n\n"
                f"**[{song.title}]({song.url})**\n\n"
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
                    view=view
                )

            else:

                self.now_playing_message = (
                    await self.text_channel.send(
                        embed=embed,
                        view=view
                    )
                )

        except Exception as e:

            print(
                "[MUSIC] ❌ EMBED ERROR:",
                repr(e)
            )


# =========================================================
# MUSIC BUTTONS
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

        if not self.player.voice:

            return await interaction.response.send_message(
                "❌ Music is not playing.",
                ephemeral=True
            )

        await interaction.response.defer()

        # Kill old callback.
        self.player.play_token += 1

        if (
            self.player.voice.is_playing()
            or self.player.voice.is_paused()
        ):

            self.player.voice.stop()

        self.player.starting = False

        await asyncio.sleep(0.4)

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

        self.player.loop = not self.player.loop

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

        # Invalidate ALL old callbacks.
        self.player.play_token += 1

        self.player.queue.clear()

        self.player.current = None

        self.player.starting = False

        if self.player.voice:

            await self.player.clear_voice_status()

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

        self.play_command_locks = {}


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

        return self.players[guild_id]


    # =====================================================
    # GET PLAY LOCK
    # =====================================================

    def get_play_lock(
        self,
        guild_id
    ):

        if guild_id not in self.play_command_locks:

            self.play_command_locks[guild_id] = (
                asyncio.Lock()
            )

        return self.play_command_locks[guild_id]


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


            # =============================================
            # DUPLICATE REQUEST PROTECTION
            # =============================================

            request_key = (
                f"{ctx.author.id}:"
                f"{str(query).strip().lower()}"
            )

            current_time = time.monotonic()

            if (
                player.last_play_request
                == request_key
                and
                current_time
                - player.last_play_request_time
                < 3.0
            ):

                print(
                    "[MUSIC] ⚠️ Duplicate play request ignored:",
                    query
                )

                return await ctx.send(
                    "⚠️ **Same play request already received.**",
                    delete_after=3
                )

            player.last_play_request = request_key
            player.last_play_request_time = current_time


            # =============================================
            # CONNECT
            # =============================================

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
                    "[MUSIC] ❌ VOICE ERROR:",
                    repr(e)
                )

                return await ctx.send(
                    "❌ Failed to connect "
                    "to the voice channel.",
                    delete_after=5
                )


            loading = await ctx.send(
                "🔎 **Loading song...**"
            )


            # =============================================
            # RESOLVE
            # =============================================

            song = await player.resolve_song(
                query,
                ctx.author
            )

            if not song:

                return await loading.edit(
                    content=(
                        "❌ **Song not found / "
                        "YouTube blocked the request.**"
                    )
                )


            try:

                await loading.delete()

            except Exception:

                pass


            # =============================================
            # CHECK CURRENT PLAYBACK
            # =============================================

            was_playing = (
                player.starting
                or
                (
                    player.voice
                    and
                    (
                        player.voice.is_playing()
                        or
                        player.voice.is_paused()
                    )
                )
                or
                player.current is not None
            )


            # =============================================
            # ADD TO QUEUE
            # =============================================

            player.queue.append(
                song
            )

            print(
                "[MUSIC] ➕ Added:",
                song.title
            )


            # =============================================
            # ALREADY PLAYING
            # =============================================

            if was_playing:

                position = len(
                    player.queue
                )

                embed = discord.Embed(
                    title="🎵 ADDED TO QUEUE",
                    description=(
                        f"**[{song.title}]({song.url})**\n\n"
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


            # =============================================
            # START MUSIC
            # =============================================

            await player.play_next()

            await asyncio.sleep(1)

            if (
                player.voice
                and
                not player.voice.is_playing()
                and
                not player.starting
            ):

                await ctx.send(
                    "❌ **Audio failed to start.**",
                    delete_after=6
                )


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
            or
            player.voice.is_paused()
        ):

            player.voice.stop()

        player.starting = False

        await asyncio.sleep(0.4)

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

        player = self.get_player(
            ctx.guild.id
        )

        if (
            player.voice
            and
            player.voice.is_playing()
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
            and
            player.voice.is_paused()
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

        player.play_token += 1

        player.queue.clear()

        player.current = None

        player.starting = False

        if player.voice:

            await player.clear_voice_status()

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

        await ctx.send(
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
                f"`{index}.` "
                f"**{song.title[:70]}**"
            )

        embed = discord.Embed(
            title="📜 HSL-CORP MUSIC QUEUE",
            description="\n".join(lines),
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
                "❌ Volume must be between "
                "`0` and `200`.",
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

        player.loop = not player.loop

        status = (
            "🟢 ON"
            if player.loop
            else "🔴 OFF"
        )

        await ctx.send(
            f"🔁 **Loop: {status}**",
            delete_after=4
        )


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
            and
            player.voice
            and
            player.current
            and
            not player.voice.is_playing()
            and
            not player.voice.is_paused()
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

async def setup(bot):

    await bot.add_cog(
        Music(bot)
    )

    print(
        "[MUSIC] ✅ Music cog loaded successfully."
    )