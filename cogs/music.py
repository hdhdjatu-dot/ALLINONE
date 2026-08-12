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
                    f"[MUSIC] [OK] Opus loaded: {path}"
                )

                return True

        except Exception as e:

            print(
                f"[MUSIC] [WARN] Opus failed {path}: {e}"
            )

    print(
        "[MUSIC] [ERROR] Opus codec NOT loaded."
    )

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
        f"[MUSIC] [COOKIE] Local cookies: {COOKIE_FILE}"
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
            "[MUSIC] [COOKIE] ENV cookies loaded."
        )

    except Exception as e:

        print(
            "[MUSIC] [ERROR] Cookie error:",
            repr(e)
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
# STATUS
# =========================================================

DISK_FRAMES = [
    "◯",
    "◉",
    "◎",
    "◉",
]

STATUS_UPDATE_INTERVAL = 2.0

MAX_QUEUE_DISPLAY = 15


# =========================================================
# FFMPEG
# =========================================================

def find_ffmpeg():

    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg:

        print(
            f"[MUSIC] [OK] FFmpeg: {ffmpeg}"
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
                f"[MUSIC] [OK] FFmpeg: {path}"
            )

            return path

    print(
        "[MUSIC] [WARN] FFmpeg not found. Using PATH."
    )

    return "ffmpeg"


FFMPEG_PATH = find_ffmpeg()


# =========================================================
# FFMPEG OPTIONS
# =========================================================

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
# YT-DLP
# =========================================================

YTDLP_OPTIONS = {

    "quiet": True,

    "no_warnings": True,

    "noplaylist": True,

    "source_address": "0.0.0.0",

    "nocheckcertificate": True,

    "geo_bypass": True,

    "socket_timeout": 10,

    "retries": 2,

    "fragment_retries": 2,

    "extractor_retries": 2,

    "continuedl": False,

    "skip_download": True,

    "http_headers": {

        "User-Agent":
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 "
            "Safari/537.36",

        "Accept-Language":
            "en-US,en;q=0.9",
    },

    "js_runtimes": {
        "deno": {}
    },

    "remote_components": [
        "ejs:github"
    ],
}


if COOKIE_FILE:

    YTDLP_OPTIONS["cookiefile"] = COOKIE_FILE


# =========================================================
# DURATION
# =========================================================

def format_duration(seconds):

    try:

        seconds = int(seconds or 0)

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
        thumbnail,
        requester,
        duration=0
    ):

        self.title = title

        self.url = url

        self.thumbnail = thumbnail

        self.requester = requester

        self.duration = duration or 0

        self.stream_url = None

        self.stream_time = 0.0


# =========================================================
# MUSIC PLAYER
# =========================================================

class MusicPlayer:

    def __init__(self, bot):

        self.bot = bot

        self.voice = None

        self.text_channel = None

        self.voice_channel = None

        self.queue = deque()

        self.current = None

        self.volume = 1.0

        self.loop = False

        self.autoplay = True

        self.starting = False

        self.play_token = 0

        self.play_lock = asyncio.Lock()

        self.now_playing_message = None

        self.status_task = None

        self.status_frame = 0

        self.autoplay_history = deque(
            maxlen=40
        )

        self.last_play_request = None

        self.last_play_request_time = 0.0

        # Prevents duplicate next-song calls
        # caused by FFmpeg callback + manual skip.
        self.transitioning = False


    # =====================================================
    # CONNECT
    # =====================================================

    async def connect_to(
        self,
        voice_channel
    ):

        try:

            if self.voice:

                if not self.voice.is_connected():

                    self.voice = None

            if self.voice:

                if self.voice.channel != voice_channel:

                    await self.voice.move_to(
                        voice_channel
                    )

            else:

                self.voice = await voice_channel.connect(
                    reconnect=True
                )

            self.voice_channel = voice_channel

            return True

        except Exception as e:

            print(
                "[MUSIC] [ERROR] Voice connect:",
                repr(e)
            )

            return False


    # =====================================================
    # YTDLP OPTIONS
    # =====================================================

    def get_ytdlp_options(
        self,
        cookies=True
    ):

        options = dict(
            YTDLP_OPTIONS
        )

        options["http_headers"] = dict(
            YTDLP_OPTIONS["http_headers"]
        )

        options["js_runtimes"] = {
            "deno": {}
        }

        options["remote_components"] = [
            "ejs:github"
        ]

        if cookies and COOKIE_FILE:

            options["cookiefile"] = COOKIE_FILE

        return options


    # =====================================================
    # RESOLVE SONG
    # =====================================================

    async def resolve_song(
        self,
        query,
        requester
    ):

        query = str(query).strip()

        if not query:

            return None

        loop = asyncio.get_running_loop()

        def extract():

            options = self.get_ytdlp_options()

            if query.startswith(
                (
                    "http://",
                    "https://"
                )
            ):

                target = query

                print(
                    "[MUSIC] [URL]:",
                    target
                )

            else:

                target = (
                    f"ytsearch1:{query}"
                )

                print(
                    "[MUSIC] [SEARCH]:",
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

                if info.get("entries"):

                    entries = [
                        x
                        for x in info["entries"]
                        if x
                    ]

                    if not entries:

                        return None

                    info = entries[0]

                url = (
                    info.get("webpage_url")
                    or info.get("original_url")
                )

                if not url:

                    video_id = info.get("id")

                    if video_id:

                        url = (
                            "https://www.youtube.com/watch?v="
                            + video_id
                        )

                if not url:

                    return None

                return {

                    "title":
                        info.get(
                            "title",
                            "Unknown Song"
                        ),

                    "url":
                        url,

                    "thumbnail":
                        info.get(
                            "thumbnail"
                        ),

                    "duration":
                        info.get(
                            "duration",
                            0
                        ),
                }

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] Resolve failed:",
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

        print(
            "[MUSIC] [OK] Selected:",
            data["title"]
        )

        return Song(
            data["title"],
            data["url"],
            data["thumbnail"],
            requester,
            data["duration"]
        )


    # =====================================================
    # AUDIO STREAM
    # =====================================================

    async def get_audio_stream(
        self,
        song
    ):

        if (
            song.stream_url
            and
            time.monotonic()
            - song.stream_time
            < 300
        ):

            return song.stream_url

        loop = asyncio.get_running_loop()

        def extract():

            try:

                options = self.get_ytdlp_options()

                options.update({

                    "skip_download": True,

                    "format":
                        (
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

                if info.get("entries"):

                    entries = [
                        x
                        for x in info["entries"]
                        if x
                    ]

                    if not entries:

                        return None

                    info = entries[0]

                stream_url = info.get(
                    "url"
                )

                if stream_url:

                    song.stream_url = stream_url

                    song.stream_time = (
                        time.monotonic()
                    )

                    if not song.thumbnail:

                        song.thumbnail = info.get(
                            "thumbnail"
                        )

                    print(
                        "[MUSIC] [OK] Fresh stream:",
                        song.title
                    )

                    return stream_url

                return None

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] Stream extraction:",
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
                "[MUSIC] [ERROR] Stream executor:",
                repr(e)
            )

            return None


    # =====================================================
    # VOICE STATUS
    # =====================================================

    async def update_voice_status(
        self,
        text
    ):

        channel = (
            self.voice_channel
            or (
                self.voice.channel
                if self.voice
                else None
            )
        )

        if not channel:

            return

        url = (
            "https://discord.com/api/v10/"
            f"channels/{channel.id}/voice-status"
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
                        "status":
                            str(text)[:500]
                    }
                ) as response:

                    if response.status not in (
                        200,
                        204
                    ):

                        print(
                            "[MUSIC] [WARN] Voice status:",
                            response.status
                        )

        except Exception as e:

            print(
                "[MUSIC] [WARN] Status error:",
                repr(e)
            )


    # =====================================================
    # CLEAR STATUS
    # =====================================================

    async def clear_voice_status(
        self
    ):

        await self.update_voice_status("")


    # =====================================================
    # STATUS ANIMATION
    # =====================================================

    async def start_status_animation(
        self
    ):

        await self.stop_status_animation(
            clear_status=False
        )

        if not self.voice_channel:

            return

        self.status_task = asyncio.create_task(
            self.status_loop()
        )


    async def status_loop(
        self
    ):

        try:

            while True:

                if not self.voice:

                    break

                if not self.voice.is_connected():

                    break

                if not self.current:

                    break

                frame = DISK_FRAMES[
                    self.status_frame
                    % len(DISK_FRAMES)
                ]

                self.status_frame += 1

                title = (
                    self.current.title
                    .strip()
                    [:460]
                )

                await self.update_voice_status(
                    f"{frame} 🎵 {title}"
                )

                await asyncio.sleep(
                    STATUS_UPDATE_INTERVAL
                )

        except asyncio.CancelledError:

            return

        except Exception as e:

            print(
                "[MUSIC] [WARN] Status loop:",
                repr(e)
            )


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

            await self.clear_voice_status()


    # =====================================================
    # AUTOPLAY
    # =====================================================

    async def resolve_autoplay_song(
        self
    ):

        if not self.current:

            return None

        previous_url = self.current.url

        previous_title = (
            self.current.title
            .lower()
            .strip()
        )

        requester = self.current.requester

        # -------------------------------------------------
        # WORDS WE DON'T CONSIDER IMPORTANT
        # -------------------------------------------------

        noise_words = {

            "official",
            "audio",
            "video",
            "lyrics",
            "lyric",
            "full",
            "song",
            "music",
            "hd",
            "4k",
            "original",
            "version",
            "visualizer",
            "mv",
            "hq",
        }

        previous_words = {

            word

            for word in (
                previous_title
                .replace("-", " ")
                .replace("_", " ")
                .replace("(", " ")
                .replace(")", " ")
                .split()
            )

            if (
                len(word) > 2
                and word not in noise_words
            )
        }

        # -------------------------------------------------
        # RELATED SEARCHES
        # -------------------------------------------------

        queries = [

            f"{self.current.title} similar songs",

            f"{self.current.title} related songs",

            f"{self.current.title} songs like this",

        ]

        loop = asyncio.get_running_loop()

        def extract():

            options = self.get_ytdlp_options()

            options["extract_flat"] = True

            candidates = []

            for search in queries:

                try:

                    print(
                        "[MUSIC] [AUTOPLAY SEARCH]:",
                        search
                    )

                    with yt_dlp.YoutubeDL(
                        options
                    ) as ydl:

                        info = ydl.extract_info(
                            f"ytsearch10:{search}",
                            download=False
                        )

                    if not info:

                        continue

                    entries = (
                        info.get("entries")
                        or []
                    )

                    for entry in entries:

                        if not entry:

                            continue

                        title = str(
                            entry.get(
                                "title",
                                ""
                            )
                        ).strip()

                        if not title:

                            continue

                        title_lower = title.lower()

                        url = (
                            entry.get(
                                "webpage_url"
                            )
                            or entry.get(
                                "original_url"
                            )
                        )

                        video_id = entry.get(
                            "id"
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

                        # -------------------------------------------------
                        # SAME URL
                        # -------------------------------------------------

                        if url == previous_url:

                            continue

                        # -------------------------------------------------
                        # HISTORY
                        # -------------------------------------------------

                        if (
                            url
                            in self.autoplay_history
                        ):

                            continue

                        # -------------------------------------------------
                        # YOUTUBE ONLY
                        # -------------------------------------------------

                        if (
                            "youtube.com" not in url
                            and
                            "youtu.be" not in url
                        ):

                            continue

                        # -------------------------------------------------
                        # CANDIDATE WORDS
                        # -------------------------------------------------

                        candidate_words = {

                            word

                            for word in (
                                title_lower
                                .replace("-", " ")
                                .replace("_", " ")
                                .replace("(", " ")
                                .replace(")", " ")
                                .split()
                            )

                            if (
                                len(word) > 2
                                and
                                word not in noise_words
                            )
                        }

                        common_words = (
                            previous_words
                            & candidate_words
                        )

                        # -------------------------------------------------
                        # SAME SONG PROTECTION
                        # -------------------------------------------------

                        if previous_words:

                            similarity = (
                                len(common_words)
                                /
                                len(previous_words)
                            )

                            if similarity >= 0.70:

                                print(
                                    "[MUSIC] "
                                    "[AUTOPLAY] "
                                    "Skipped same song:",
                                    title
                                )

                                continue

                        # -------------------------------------------------
                        # SAME-SONG VERSIONS
                        # -------------------------------------------------

                        version_words = (

                            "remix",

                            "slowed",

                            "reverb",

                            "sped up",

                            "speed up",

                            "nightcore",

                            "8d",

                            "bass boosted",

                            "karaoke",

                            "instrumental",

                            "cover",

                            "lofi",

                            "lo-fi",

                        )

                        if any(
                            word in title_lower
                            for word in version_words
                        ):

                            if common_words:

                                print(
                                    "[MUSIC] "
                                    "[AUTOPLAY] "
                                    "Skipped version:",
                                    title
                                )

                                continue

                        candidates.append(
                            entry
                        )

                except Exception as e:

                    print(
                        "[MUSIC] [WARN] "
                        "Autoplay search:",
                        repr(e)
                    )

            # -------------------------------------------------
            # REMOVE DUPLICATES
            # -------------------------------------------------

            unique = {}

            for entry in candidates:

                url = (
                    entry.get(
                        "webpage_url"
                    )
                    or entry.get(
                        "original_url"
                    )
                )

                video_id = entry.get(
                    "id"
                )

                if (
                    not url
                    and video_id
                ):

                    url = (
                        "https://www.youtube.com/watch?v="
                        + video_id
                    )

                if url:

                    unique[url] = entry

            candidates = list(
                unique.values()
            )

            if not candidates:

                return None

            # -------------------------------------------------
            # PICK RANDOM VALID RELATED SONG
            # -------------------------------------------------

            return random.choice(
                candidates[:15]
            )

        try:

            entry = await loop.run_in_executor(
                None,
                extract
            )

        except Exception as e:

            print(
                "[MUSIC] [ERROR] "
                "Autoplay executor:",
                repr(e)
            )

            return None

        if not entry:

            return None

        url = (
            entry.get(
                "webpage_url"
            )
            or entry.get(
                "original_url"
            )
        )

        video_id = entry.get(
            "id"
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

            return None

        if url == previous_url:

            return None

        if url in self.autoplay_history:

            return None

        song = Song(

            entry.get(
                "title",
                "Unknown Song"
            ),

            url,

            entry.get(
                "thumbnail"
            ),

            requester,

            entry.get(
                "duration",
                0
            )
        )

        self.autoplay_history.append(
            song.url
        )

        print(
            "[MUSIC] [AUTOPLAY] RELATED:",
            song.title
        )

        return song


    # =====================================================
    # PLAY NEXT
    # =====================================================

    async def play_next(
        self
    ):

        # -------------------------------------------------
        # ONLY ONE PLAY TRANSITION AT A TIME
        # -------------------------------------------------

        async with self.play_lock:

            if not self.voice:

                return

            if not self.voice.is_connected():

                return

            if self.starting:

                return

            self.starting = True

            try:

                # -----------------------------------------
                # LOOP
                # -----------------------------------------

                if (
                    self.loop
                    and self.current
                ):

                    song = self.current

                    song.stream_url = None

                    song.stream_time = 0

                # -----------------------------------------
                # QUEUE
                # -----------------------------------------

                elif self.queue:

                    song = self.queue.popleft()

                    self.current = song

                # -----------------------------------------
                # AUTOPLAY
                # -----------------------------------------

                elif (
                    self.autoplay
                    and self.current
                ):

                    print(
                        "[MUSIC] [AUTOPLAY] "
                        "Finding related song..."
                    )

                    song = (
                        await self.resolve_autoplay_song()
                    )

                    if not song:

                        print(
                            "[MUSIC] [AUTOPLAY] "
                            "No valid related song found."
                        )

                        await self.stop_status_animation()

                        self.current = None

                        return

                    self.current = song

                # -----------------------------------------
                # NOTHING
                # -----------------------------------------

                else:

                    self.current = None

                    await self.stop_status_animation()

                    return

                # -----------------------------------------
                # NEW TOKEN
                # -----------------------------------------

                self.play_token += 1

                token = self.play_token

                # -----------------------------------------
                # STOP OLD AUDIO
                # -----------------------------------------

                if (
                    self.voice.is_playing()
                    or self.voice.is_paused()
                ):

                    self.voice.stop()

                    await asyncio.sleep(
                        0.05
                    )

                # -----------------------------------------
                # STREAM
                # -----------------------------------------

                stream_url = (
                    await self.get_audio_stream(
                        song
                    )
                )

                if not stream_url:

                    print(
                        "[MUSIC] [ERROR] "
                        "No stream:",
                        song.title
                    )

                    # Do NOT recursively call play_next
                    # while holding play_lock.
                    # This was one of the old deadlock bugs.
                    self.current = None

                    return

                # -----------------------------------------
                # FFMPEG
                # -----------------------------------------

                source = discord.FFmpegPCMAudio(

                    stream_url,

                    executable=FFMPEG_PATH,

                    before_options=(
                        FFMPEG_BEFORE_OPTIONS
                    ),

                    options=(
                        FFMPEG_OPTIONS
                    )
                )

                source = discord.PCMVolumeTransformer(
                    source,
                    volume=self.volume
                )

                # -----------------------------------------
                # CALLBACK
                # -----------------------------------------

                def after_play(error):

                    if error:

                        print(
                            "[MUSIC] [ERROR] "
                            "Playback:",
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
                            "Callback:",
                            repr(e)
                        )

                # -----------------------------------------
                # OLD TOKEN
                # -----------------------------------------

                if token != self.play_token:

                    return

                # -----------------------------------------
                # PLAY
                # -----------------------------------------

                self.voice.play(
                    source,
                    after=after_play
                )

                print(
                    "[MUSIC] [PLAYING]:",
                    song.title
                )

                # -----------------------------------------
                # NOW PLAYING
                # -----------------------------------------

                await self.send_now_playing()

                # -----------------------------------------
                # STATUS
                # -----------------------------------------

                await self.start_status_animation()

            except Exception as e:

                print(
                    "[MUSIC] [ERROR] Play next:",
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

        # -------------------------------------------------
        # OLD CALLBACK = IGNORE
        # -------------------------------------------------

        if token != self.play_token:

            return

        await asyncio.sleep(
            0.12
        )

        if token != self.play_token:

            return

        if not self.voice:

            return

        if not self.voice.is_connected():

            return

        if (
            self.voice.is_playing()
            or self.voice.is_paused()
        ):

            return

        # -------------------------------------------------
        # PREVENT CALLBACK/USER SKIP COLLISION
        # -------------------------------------------------

        if self.transitioning:

            return

        print(
            "[MUSIC] [FINISHED]:",
            (
                self.current.title
                if self.current
                else "Unknown"
            )
        )

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
                "HSL-CORP • "
                "Ultra Fast Music System"
            )
        )

        view = MusicControlView(
            self
        )

        try:

            if self.now_playing_message:

                await self.now_playing_message.edit(

                    content=None,

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

        except discord.NotFound:

            self.now_playing_message = (
                await self.text_channel.send(
                    embed=embed,
                    view=view
                )
            )

        except Exception as e:

            print(
                "[MUSIC] [ERROR] Now Playing:",
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

        player = self.player

        if not player.voice:

            return await interaction.response.send_message(
                "❌ Music is not playing.",
                ephemeral=True
            )

        await interaction.response.defer()

        # -------------------------------------------------
        # PREVENT DOUBLE TRANSITION
        # -------------------------------------------------

        if player.transitioning:

            return

        player.transitioning = True

        try:

            # -------------------------------------------------
            # INVALIDATE OLD CALLBACK
            # -------------------------------------------------

            player.play_token += 1

            voice = player.voice

            if (
                voice.is_playing()
                or voice.is_paused()
            ):

                voice.stop()

            # -------------------------------------------------
            # WAIT FOR OLD CALLBACK
            # -------------------------------------------------

            await asyncio.sleep(
                0.15
            )

            player.starting = False

            # -------------------------------------------------
            # PLAY EXACTLY ONE NEXT SONG
            # -------------------------------------------------

            await player.play_next()

        finally:

            player.transitioning = False


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

        player.play_token += 1

        player.transitioning = True

        player.queue.clear()

        player.autoplay_history.clear()

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

        player.voice = None

        player.voice_channel = None

        player.text_channel = None

        player.now_playing_message = None

        player.transitioning = False

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
                MusicPlayer(self.bot)
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

            player.text_channel = ctx.channel

            player.voice_channel = voice_channel

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
                -
                player.last_play_request_time
                < 3
            ):

                return await ctx.send(
                    "⚠️ **Same play request already received.**",
                    delete_after=3
                )

            player.last_play_request = (
                request_key
            )

            player.last_play_request_time = (
                current_time
            )

            connected = await player.connect_to(
                voice_channel
            )

            if not connected:

                return await ctx.send(
                    "❌ Failed to connect to voice channel.",
                    delete_after=5
                )

            # -------------------------------------------------
            # NEW COOL LOADING MESSAGE
            # -------------------------------------------------

            loading = await ctx.send(
                "🎧 **Tuning in...**"
            )

            song = await player.resolve_song(
                query,
                ctx.author
            )

            if not song:

                return await loading.edit(
                    content=(
                        "❌ **Song not found.**\n"
                        "YouTube request failed."
                    )
                )

            try:

                await loading.delete()

            except Exception:

                pass

            was_playing = (

                player.starting

                or (
                    player.voice
                    and (
                        player.voice.is_playing()
                        or
                        player.voice.is_paused()
                    )
                )

                or player.current is not None
            )

            player.queue.append(
                song
            )

            print(
                "[MUSIC] [QUEUE]:",
                song.title
            )

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

                await ctx.send(
                    embed=embed,
                    delete_after=8
                )

                return

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

        # -------------------------------------------------
        # PREVENT DOUBLE SKIP RACE
        # -------------------------------------------------

        if player.transitioning:

            return await ctx.send(
                "⏭️ **Already skipping...**",
                delete_after=2
            )

        player.transitioning = True

        try:

            # -------------------------------------------------
            # INVALIDATE OLD CALLBACK
            # -------------------------------------------------

            player.play_token += 1

            voice = player.voice

            if (
                voice.is_playing()
                or voice.is_paused()
            ):

                voice.stop()

            await asyncio.sleep(
                0.15
            )

            player.starting = False

            await player.play_next()

        finally:

            player.transitioning = False


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

        if not ctx.guild:

            return

        player = self.get_player(
            ctx.guild.id
        )

        player.play_token += 1

        player.transitioning = True

        player.queue.clear()

        player.autoplay_history.clear()

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

        player.voice = None

        player.voice_channel = None

        player.text_channel = None

        player.now_playing_message = None

        player.transitioning = False

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

        if not ctx.guild:

            return

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
            list(player.queue)[
                :MAX_QUEUE_DISPLAY
            ],
            1
        ):

            lines.append(

                f"`{index}.` "
                f"**{song.title[:70]}** "
                f"`{format_duration(song.duration)}`"
            )

        embed = discord.Embed(

            title="📜 HSL-CORP MUSIC QUEUE",

            description="\n".join(lines),

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

        if not ctx.guild:

            return

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

        if not ctx.guild:

            return

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

        if not ctx.guild:

            return

        player = self.get_player(
            ctx.guild.id
        )

        if not player.current:

            return await ctx.send(
                "📭 **Nothing is playing.**",
                delete_after=4
            )

        player.text_channel = ctx.channel

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
        "HSL-CORP ULTRA FAST MUSIC SYSTEM LOADED"
    )