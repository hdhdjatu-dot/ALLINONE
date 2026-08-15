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
            print(
                f"[MUSIC] [WARN] Failed to load Opus "
                f"{path}: {e}"
            )

    print("[MUSIC] [ERROR] Opus codec NOT loaded.")
    return False


OPUS_LOADED = load_opus()

if not OPUS_LOADED:
    print(
        "[MUSIC] [WARN] Discord voice audio cannot play "
        "until Opus is available."
    )


# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
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

        cookie_dir = (
            "/tmp"
            if os.name != "nt"
            else BASE_DIR
        )

        COOKIE_FILE = os.path.join(
            cookie_dir,
            "youtube_cookies.txt"
        )

        with open(
            COOKIE_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(YOUTUBE_COOKIES)

        print(
            "[MUSIC] [COOKIE] Cookies loaded "
            "from environment."
        )

    except Exception as e:

        print(
            f"[MUSIC] [ERROR] Cookie file error: "
            f"{e!r}"
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

        print(
            f"[MUSIC] [OK] FFmpeg found: {ffmpeg}"
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
                f"[MUSIC] [OK] FFmpeg found: {path}"
            )

            return path

    print(
        "[MUSIC] [WARN] FFmpeg not found. "
        "Using 'ffmpeg' command."
    )

    return "ffmpeg"


FFMPEG_PATH = find_ffmpeg()


# =========================================================
# YOUTUBE USER AGENT
# =========================================================

YOUTUBE_USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/151.0.0.0 "
    "Safari/537.36"
)


# =========================================================
# YT-DLP BASE OPTIONS
# =========================================================

YTDLP_OPTIONS = {

    "quiet": True,

    "no_warnings": True,

    "noplaylist": True,

    "source_address": "0.0.0.0",

    "http_headers": {

        "User-Agent":
            YOUTUBE_USER_AGENT,

        "Accept-Language":
            "en-US,en;q=0.9",

        "Accept":
            "*/*",

        "Referer":
            "https://www.youtube.com/",
    },

    "socket_timeout": 30,

    "retries": 5,

    "fragment_retries": 5,

    "file_access_retries": 3,

    "extractor_retries": 3,

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

        # Every playback gets unique token.
        self.play_token = 0

        self.play_lock = asyncio.Lock()

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

        self.stopping = False


    # =====================================================
    # INVALIDATE PLAYBACK
    # =====================================================

    def invalidate_playback(self):

        self.play_token += 1

        print(
            f"[MUSIC] [TOKEN] "
            f"Playback invalidated -> {self.play_token}"
        )

        return self.play_token


    # =====================================================
    # VOICE STATUS
    # =====================================================

    async def update_voice_status(self, text):

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

                    if response.status in (200, 204):

                        print(
                            "[MUSIC] [OK] "
                            "VC status updated:",
                            text
                        )

                    else:

                        error = await response.text()

                        print(
                            "[MUSIC] [WARN] "
                            f"VC status failed "
                            f"({response.status}): "
                            f"{error}"
                        )

        except Exception as e:

            print(
                "[MUSIC] [WARN] "
                f"VC status error: {e!r}"
            )


    # =====================================================
    # CLEAR VOICE STATUS
    # =====================================================

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

                async with session.put(
                    url,
                    headers=headers,
                    json={
                        "status": ""
                    }
                ) as response:

                    if response.status in (200, 204):

                        print(
                            "[MUSIC] [OK] "
                            "VC status cleared."
                        )

        except Exception as e:

            print(
                "[MUSIC] [WARN] "
                f"VC status clear error: {e!r}"
            )


    # =====================================================
    # YTDLP OPTIONS
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

            if query.startswith(
                (
                    "http://",
                    "https://"
                )
            ):

                target = query

                print(
                    "[MUSIC] [URL] Direct URL:",
                    target
                )

            else:

                target = (
                    f"ytsearch1:{query}"
                )

                print(
                    "[MUSIC] [SEARCH] Searching:",
                    query
                )

            try:

                options = self.get_ytdlp_options(
                    use_cookies=bool(COOKIE_FILE)
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
                    return None

                if "entries" in info:

                    entries = [
                        entry
                        for entry in (
                            info.get("entries") or []
                        )
                        if entry
                    ]

                    if not entries:
                        return None

                    info = entries[0]

                webpage_url = (
                    info.get("webpage_url")
                    or info.get("original_url")
                )

                if not webpage_url:

                    video_id = info.get("id")

                    if video_id:

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
                        info.get("thumbnail"),
                }

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] "
                    "YouTube resolve failed:",
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
                "[MUSIC] [ERROR] "
                f"Resolve error: {e!r}"
            )

            return None

        if not data:
            return None

        print(
            "[MUSIC] [OK] Selected:",
            data["title"]
        )

        return Song(
            data["title"],
            data["url"],
            data["thumbnail"],
            requester
        )


    # =====================================================
    # GET FRESH AUDIO STREAM
    # =====================================================

    async def get_audio_stream(
        self,
        song
    ):

        loop = asyncio.get_running_loop()

        def extract():

            try:

                options = self.get_ytdlp_options(
                    use_cookies=bool(COOKIE_FILE)
                )

                options.update({

                    "skip_download": True,

                    "format": (
                        "bestaudio[ext=webm]/"
                        "bestaudio[ext=m4a]/"
                        "bestaudio/best"
                    ),

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
                        entry
                        for entry in (
                            info.get("entries") or []
                        )
                        if entry
                    ]

                    if not entries:
                        return None

                    info = entries[0]

                stream_url = info.get("url")

                if not stream_url:
                    return None

                # IMPORTANT:
                # yt-dlp may return headers specifically
                # required by the generated Googlevideo URL.
                stream_headers = (
                    info.get("http_headers")
                    or {}
                )

                # Ensure User-Agent exists.
                if not stream_headers.get("User-Agent"):

                    stream_headers["User-Agent"] = (
                        YOUTUBE_USER_AGENT
                    )

                if not stream_headers.get("Referer"):

                    stream_headers["Referer"] = (
                        "https://www.youtube.com/"
                    )

                print(
                    "[MUSIC] [OK] Fresh audio stream obtained."
                )

                return {
                    "url": stream_url,
                    "headers": stream_headers
                }

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] "
                    "Audio stream extraction failed:",
                    repr(e)
                )

                return None

        try:

            return await loop.run_in_executor(
                None,
                extract
            )

        except Exception as e:

            print(
                "[MUSIC] [ERROR] "
                f"Audio error: {e!r}"
            )

            return None


    # =====================================================
    # BUILD FFMPEG HEADERS
    # =====================================================

    def build_ffmpeg_headers(
        self,
        headers
    ):

        if not headers:
            return ""

        lines = []

        for key, value in headers.items():

            if not key or value is None:
                continue

            # FFmpeg header escaping.
            key = str(key).replace(
                "\r", ""
            ).replace(
                "\n", ""
            )

            value = str(value).replace(
                "\r", ""
            ).replace(
                "\n", ""
            )

            lines.append(
                f"{key}: {value}"
            )

        if not lines:
            return ""

        return (
            "\r\n".join(lines)
            + "\r\n"
        )


    # =====================================================
    # AUTOPLAY
    # =====================================================

    async def resolve_autoplay_song(self):

        if not self.current:
            return None

        loop = asyncio.get_running_loop()

        requester = self.current.requester

        previous_url = self.current.url

        previous_title = (
            self.current.title
            .lower()
            .strip()
        )

        autoplay_queries = [

            "Hindi songs",

            "Bollywood songs",

            "latest Hindi music",

            "popular Hindi songs",

            "Hindi romantic songs",

            "trending Bollywood songs",

            "best Bollywood songs",

            "Indian music",

        ]

        random.shuffle(
            autoplay_queries
        )

        history_urls = set(
            self.autoplay_history
        )

        recent_urls = set(
            self.play_history
        )

        def extract():

            options = self.get_ytdlp_options(
                use_cookies=bool(COOKIE_FILE)
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

                        if not title:
                            continue

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

                        if url in history_urls:
                            continue

                        if url in recent_urls:
                            continue

                        if (
                            "youtube.com" not in url
                            and
                            "youtu.be" not in url
                        ):
                            continue

                        valid.append(entry)

                    if valid:

                        entry = random.choice(valid)

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
                            "title":
                                entry.get(
                                    "title",
                                    "Unknown Song"
                                ),

                            "url":
                                url,

                            "thumbnail":
                                entry.get(
                                    "thumbnail"
                                ),
                        }

                except Exception as e:

                    print(
                        "[MUSIC] [WARN] "
                        "Autoplay search failed:",
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
                "[MUSIC] [ERROR] "
                "Autoplay search error:",
                repr(e)
            )

            return None

        if not data:
            return None

        print(
            "[MUSIC] [AUTOPLAY] Selected:",
            data["title"]
        )

        song = Song(
            data["title"],
            data["url"],
            data.get("thumbnail"),
            requester
        )

        self.autoplay_history.append(
            song.url
        )

        self.play_history.append(
            song.url
        )

        return song


    # =====================================================
    # START NEXT SONG
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

                # Maximum attempts so one broken YouTube
                # stream cannot create an infinite loop.
                attempts = 0

                max_attempts = 4

                while attempts < max_attempts:

                    attempts += 1

                    if not self.voice:
                        return

                    if not self.voice.is_connected():
                        return

                    # -------------------------------------
                    # SELECT SONG
                    # -------------------------------------

                    if (
                        self.loop
                        and self.current
                    ):

                        song = self.current

                    elif self.queue:

                        song = self.queue.popleft()

                        self.current = song

                    elif (
                        self.autoplay
                        and self.current
                    ):

                        print(
                            "[MUSIC] [AUTOPLAY] Searching..."
                        )

                        song = (
                            await self.resolve_autoplay_song()
                        )

                        if not song:

                            print(
                                "[MUSIC] [WARN] "
                                "Autoplay found no song."
                            )

                            self.current = None

                            await self.clear_voice_status()

                            return

                        self.current = song

                    else:

                        self.current = None

                        await self.clear_voice_status()

                        return

                    # -------------------------------------
                    # NEW TOKEN
                    # -------------------------------------

                    self.play_token += 1

                    token = self.play_token

                    print(
                        "[MUSIC] [PREPARE]:",
                        song.title,
                        "| token:",
                        token
                    )

                    # -------------------------------------
                    # STOP OLD AUDIO
                    # -------------------------------------

                    if (
                        self.voice.is_playing()
                        or self.voice.is_paused()
                    ):

                        self.voice.stop()

                        await asyncio.sleep(0.08)

                    # -------------------------------------
                    # FRESH STREAM
                    # -------------------------------------

                    stream_data = (
                        await self.get_audio_stream(song)
                    )

                    # -------------------------------------
                    # TOKEN CHECK
                    # -------------------------------------

                    if token != self.play_token:

                        print(
                            "[MUSIC] [WARN] "
                            "Playback cancelled "
                            "before FFmpeg start."
                        )

                        return

                    # -------------------------------------
                    # STREAM FAILED
                    # -------------------------------------

                    if not stream_data:

                        print(
                            "[MUSIC] [ERROR] "
                            "Stream unavailable:",
                            song.title
                        )

                        # If queue contains songs, try next.
                        if self.queue:

                            self.current = None

                            continue

                        # If autoplay is on, get another song.
                        if self.autoplay:

                            print(
                                "[MUSIC] [AUTOPLAY RETRY] "
                                "Trying another song."
                            )

                            # Prevent the same current song
                            # from being selected repeatedly.
                            if song.url not in self.autoplay_history:

                                self.autoplay_history.append(
                                    song.url
                                )

                            continue

                        self.current = None

                        await self.clear_voice_status()

                        return

                    stream_url = stream_data["url"]

                    stream_headers = (
                        stream_data.get("headers")
                        or {}
                    )

                    ffmpeg_headers = (
                        self.build_ffmpeg_headers(
                            stream_headers
                        )
                    )

                    # -------------------------------------
                    # FFMPEG BEFORE OPTIONS
                    # -------------------------------------

                    before_options = (
                        "-reconnect 1 "
                        "-reconnect_streamed 1 "
                        "-reconnect_at_eof 1 "
                        "-reconnect_on_network_error 1 "
                        "-reconnect_on_http_error "
                        "403,404,429,500,502,503,504 "
                        "-reconnect_delay_max 5 "
                        "-nostdin"
                    )

                    if ffmpeg_headers:

                        before_options += (
                            " -headers "
                            f'"{ffmpeg_headers}"'
                        )

                    # -------------------------------------
                    # FFMPEG OPTIONS
                    # -------------------------------------

                    ffmpeg_options = (
                        "-vn "
                        "-loglevel error "
                        "-ar 48000 "
                        "-ac 2 "
                        "-bufsize 512k"
                    )

                    # -------------------------------------
                    # CREATE SOURCE
                    # -------------------------------------

                    try:

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

                    except Exception as e:

                        print(
                            "[MUSIC] [ERROR] "
                            "FFmpeg source creation failed:",
                            repr(e)
                        )

                        self.current = None

                        continue

                    # -------------------------------------
                    # CALLBACK
                    # -------------------------------------

                    def after_play(error):

                        if error:

                            print(
                                "[MUSIC] [ERROR] "
                                "Playback callback:",
                                repr(error)
                            )

                        try:

                            asyncio.run_coroutine_threadsafe(
                                self.finished(token),
                                self.bot.loop
                            )

                        except Exception as e:

                            print(
                                "[MUSIC] [ERROR] "
                                "Finish callback:",
                                repr(e)
                            )

                    # -------------------------------------
                    # FINAL TOKEN CHECK
                    # -------------------------------------

                    if token != self.play_token:

                        print(
                            "[MUSIC] [WARN] "
                            "Old playback ignored."
                        )

                        try:
                            source.cleanup()
                        except Exception:
                            pass

                        return

                    # -------------------------------------
                    # START
                    # -------------------------------------

                    try:

                        self.voice.play(
                            source,
                            after=after_play
                        )

                    except Exception as e:

                        print(
                            "[MUSIC] [ERROR] "
                            "voice.play failed:",
                            repr(e)
                        )

                        try:
                            source.cleanup()
                        except Exception:
                            pass

                        self.current = None

                        continue

                    print(
                        "[MUSIC] [PLAYING]:",
                        song.title,
                        "| token:",
                        token
                    )

                    # -------------------------------------
                    # VOICE STATUS
                    # -------------------------------------

                    await self.update_voice_status(
                        f"🎵 {song.title}"
                    )

                    # -------------------------------------
                    # NOW PLAYING
                    # -------------------------------------

                    await self.send_now_playing()

                    return

                # -----------------------------------------
                # ALL ATTEMPTS FAILED
                # -----------------------------------------

                print(
                    "[MUSIC] [ERROR] "
                    "All playback attempts failed."
                )

                self.current = None

                await self.clear_voice_status()

            except asyncio.CancelledError:

                raise

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] "
                    "Playback error:",
                    repr(e)
                )

            finally:

                self.starting = False


    # =====================================================
    # FINISHED
    # =====================================================

    async def finished(self, token):

        if token != self.play_token:

            print(
                "[MUSIC] [CALLBACK] "
                "Old callback ignored:",
                token,
                "!=",
                self.play_token
            )

            return

        await asyncio.sleep(0.15)

        if token != self.play_token:
            return

        if (
            not self.voice
            or not self.voice.is_connected()
        ):
            return

        if (
            self.voice.is_playing()
            or self.voice.is_paused()
        ):
            return

        print(
            "[MUSIC] [FINISHED] "
            "Starting next song."
        )

        await self.play_next()


    # =====================================================
    # NOW PLAYING
    # =====================================================

    async def send_now_playing(self):

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

        view = MusicControlView(self)

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

            try:

                self.now_playing_message = (
                    await self.text_channel.send(
                        embed=embed,
                        view=view
                    )
                )

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] "
                    "Now playing resend:",
                    repr(e)
                )

        except Exception as e:

            print(
                "[MUSIC] [ERROR] "
                "Embed error:",
                repr(e)
            )


# =========================================================
# MUSIC BUTTONS
# =========================================================

class MusicControlView(discord.ui.View):

    def __init__(self, player):

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
    # SKIP BUTTON
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

        await interaction.response.defer()

        if player.skip_lock.locked():

            try:

                await interaction.followup.send(
                    "⚠️ Skip already processing.",
                    ephemeral=True
                )

            except Exception:
                pass

            return

        async with player.skip_lock:

            player.invalidate_playback()

            if (
                player.voice
                and (
                    player.voice.is_playing()
                    or player.voice.is_paused()
                )
            ):

                player.voice.stop()

                await asyncio.sleep(0.08)

            player.starting = False

            await player.play_next()


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

        player = self.player

        player.invalidate_playback()

        player.queue.clear()

        player.current = None

        player.starting = False

        player.autoplay_history.clear()

        player.play_history.clear()

        if player.voice:

            await player.clear_voice_status()

            if (
                player.voice.is_playing()
                or player.voice.is_paused()
            ):

                player.voice.stop()

                await asyncio.sleep(0.08)

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

class Music(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.players = {}

        self.play_command_locks = {}


    # =====================================================
    # GET PLAYER
    # =====================================================

    def get_player(self, guild_id):

        if guild_id not in self.players:

            self.players[guild_id] = (
                MusicPlayer(self.bot)
            )

        return self.players[guild_id]


    # =====================================================
    # GET PLAY LOCK
    # =====================================================

    def get_play_lock(self, guild_id):

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
                "❌ This command can only be used in a server.",
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

            voice_channel = (
                ctx.author.voice.channel
            )

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

                return await ctx.send(
                    "⚠️ **Same play request already received.**",
                    delete_after=3
                )

            player.last_play_request = request_key

            player.last_play_request_time = current_time

            # ---------------------------------------------
            # TEXT CHANNEL
            # ---------------------------------------------

            if player.text_channel is None:

                player.text_channel = ctx.channel

            elif (
                player.current is None
                and not player.voice
            ):

                player.text_channel = ctx.channel

            # ---------------------------------------------
            # CONNECT VOICE
            # ---------------------------------------------

            try:

                if ctx.voice_client:

                    player.voice = ctx.voice_client

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
                    "[MUSIC] [ERROR] "
                    "Voice error:",
                    repr(e)
                )

                return await ctx.send(
                    "❌ Failed to connect to the voice channel.",
                    delete_after=5
                )

            # ---------------------------------------------
            # LOADING
            # ---------------------------------------------

            loading = await ctx.send(
                "🔎 **Loading song...**"
            )

            song = await player.resolve_song(
                query,
                ctx.author
            )

            if not song:

                try:

                    await loading.edit(
                        content=(
                            "❌ **YouTube could not provide "
                            "this song right now.**"
                        )
                    )

                except Exception:
                    pass

                return

            try:

                await loading.delete()

            except Exception:
                pass

            player.last_manual_query = str(query)

            # ---------------------------------------------
            # WAS PLAYING?
            # ---------------------------------------------

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
                or len(player.queue) > 0
            )

            # ---------------------------------------------
            # HISTORY
            # ---------------------------------------------

            player.play_history.append(
                song.url
            )

            # ---------------------------------------------
            # QUEUE
            # ---------------------------------------------

            player.queue.append(song)

            print(
                "[MUSIC] [QUEUE] Added:",
                song.title
            )

            # ---------------------------------------------
            # ALREADY PLAYING
            # ---------------------------------------------

            if was_playing:

                position = len(player.queue)

                embed = discord.Embed(

                    title="🎵 ADDED TO QUEUE",

                    description=(
                        f"**[{song.title}]"
                        f"({song.url})**\n\n"
                        f"👤 "
                        f"{ctx.author.mention}\n"
                        f"📍 Position: "
                        f"`{position}`"
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

            # ---------------------------------------------
            # START
            # ---------------------------------------------

            await player.play_next()

            await asyncio.sleep(0.7)

            if (
                player.voice
                and not player.voice.is_playing()
                and not player.starting
                and player.current
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
    async def skip(self, ctx):

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
                "⚠️ **Skip already processing.**",
                delete_after=3
            )

        async with player.skip_lock:

            player.invalidate_playback()

            if (
                player.voice.is_playing()
                or player.voice.is_paused()
            ):

                player.voice.stop()

                await asyncio.sleep(0.08)

            player.starting = False

            await player.play_next()

        try:

            if ctx.message:

                await ctx.message.delete()

        except Exception:

            pass


    # =====================================================
    # PAUSE
    # =====================================================

    @commands.hybrid_command(
        name="pause",
        description="Pause music"
    )
    async def pause(self, ctx):

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
    async def resume(self, ctx):

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
    async def stop(self, ctx):

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

            await player.clear_voice_status()

            if (
                player.voice.is_playing()
                or player.voice.is_paused()
            ):

                player.voice.stop()

                await asyncio.sleep(0.08)

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
    async def queue(self, ctx):

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
                "❌ Volume must be between `0` and `200`.",
                delete_after=4
            )

        player = self.get_player(
            ctx.guild.id
        )

        player.volume = amount / 100

        if player.voice:

            source = player.voice.source

            if isinstance(
                source,
                discord.PCMVolumeTransformer
            ):

                source.volume = amount / 100

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
    async def loop(self, ctx):

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
    async def autoplay(self, ctx):

        player = self.get_player(
            ctx.guild.id
        )

        player.autoplay = not player.autoplay

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
    async def nowplaying(self, ctx):

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
        "[MUSIC] [OK] "
        "Music cog loaded successfully."
    )