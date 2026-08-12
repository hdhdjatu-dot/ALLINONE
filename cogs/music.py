import asyncio
import os
import shutil
import ctypes
import ctypes.util
import random
import time
import re
from collections import deque

import aiohttp
import discord
from discord.ext import commands
import yt_dlp


# ============================================================
# HSL-CORP ULTRA MUSIC SYSTEM
# ============================================================


# ============================================================
# OPUS
# ============================================================

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
        r"C:\ffmpeg\bin\opus.dll",
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


# ============================================================
# BASE DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# ============================================================
# YOUTUBE COOKIES
# ============================================================

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

        print("[MUSIC] [COOKIE] ENV cookies loaded.")

    except Exception as e:

        print(
            "[MUSIC] [ERROR] Cookie error:",
            repr(e)
        )

else:

    print(
        "[MUSIC] [WARN] YouTube cookies not found."
    )


# ============================================================
# HSL GIF
# ============================================================

HSL_GIF = (
    "https://media3.giphy.com/media/"
    "v1.Y2lkPTc5MGI3NjExZ3RqemR3c3A0MHl3NWw1NHE4a2FjdWVkdDdqdXppaXdxdHhobGF5ayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/"
    "iBILBPeCHDVuELjOND/giphy.gif"
)


# ============================================================
# STATUS
# ============================================================

DISK_FRAMES = [
    "◢",
    "◣",
    "◤",
    "◥",
]

STATUS_UPDATE_INTERVAL = 2.0
MAX_QUEUE_DISPLAY = 15


# ============================================================
# FFMPEG
# ============================================================

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


# ============================================================
# FFMPEG OPTIONS
# ============================================================

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


# ============================================================
# YT-DLP BASE OPTIONS
# ============================================================

YTDLP_OPTIONS = {

    "quiet": True,

    "no_warnings": True,

    "noplaylist": True,

    "source_address": "0.0.0.0",

    "nocheckcertificate": True,

    "geo_bypass": True,

    "socket_timeout": 15,

    "retries": 3,

    "fragment_retries": 3,

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
}


if COOKIE_FILE:
    YTDLP_OPTIONS["cookiefile"] = COOKIE_FILE


# ============================================================
# DURATION
# ============================================================

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


# ============================================================
# NORMALIZE TITLE
# ============================================================

def normalize_title(title):

    title = str(title or "").lower()

    title = re.sub(
        r"\[[^\]]*\]",
        " ",
        title
    )

    title = re.sub(
        r"\([^)]*\)",
        " ",
        title
    )

    title = re.sub(
        r"\b(official|video|audio|lyrics?|lyric|hd|4k|remix|"
        r"slowed|reverb|visualizer|full song|full video)\b",
        " ",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"[^a-z0-9\u0900-\u097f\s]",
        " ",
        title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


# ============================================================
# SONG
# ============================================================

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


# ============================================================
# MUSIC PLAYER
# ============================================================

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
            maxlen=50
        )

        self.last_play_request = None

        self.last_play_request_time = 0.0


# ============================================================
# CONNECT
# ============================================================

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


# ============================================================
# YTDLP OPTIONS
# ============================================================

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

        if cookies and COOKIE_FILE:

            options["cookiefile"] = COOKIE_FILE

        return options


# ============================================================
# SEARCH EXTRACTION
# ============================================================

    async def youtube_search(
        self,
        query,
        limit=5
    ):

        loop = asyncio.get_running_loop()

        def extract():

            options = self.get_ytdlp_options()

            options["extract_flat"] = True

            search_target = (
                f"ytsearch{limit}:{query}"
            )

            try:

                with yt_dlp.YoutubeDL(
                    options
                ) as ydl:

                    info = ydl.extract_info(
                        search_target,
                        download=False
                    )

                if not info:
                    return []

                return [
                    entry
                    for entry in (
                        info.get("entries")
                        or []
                    )
                    if entry
                ]

            except Exception as e:

                print(
                    "[MUSIC] [SEARCH ERROR]:",
                    repr(e)
                )

                try:

                    fallback = dict(
                        YTDLP_OPTIONS
                    )

                    fallback.pop(
                        "cookiefile",
                        None
                    )

                    fallback["extract_flat"] = True

                    with yt_dlp.YoutubeDL(
                        fallback
                    ) as ydl:

                        info = ydl.extract_info(
                            search_target,
                            download=False
                        )

                    if not info:
                        return []

                    return [
                        entry
                        for entry in (
                            info.get("entries")
                            or []
                        )
                        if entry
                    ]

                except Exception as e2:

                    print(
                        "[MUSIC] [SEARCH FALLBACK ERROR]:",
                        repr(e2)
                    )

                    return []

        try:

            return await loop.run_in_executor(
                None,
                extract
            )

        except Exception as e:

            print(
                "[MUSIC] [SEARCH EXECUTOR ERROR]:",
                repr(e)
            )

            return []


# ============================================================
# RESOLVE SONG
# ============================================================

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

                return info

            except Exception as e:

                print(
                    "[MUSIC] [PRIMARY RESOLVE ERROR]:",
                    repr(e)
                )

                try:

                    fallback = dict(
                        YTDLP_OPTIONS
                    )

                    fallback.pop(
                        "cookiefile",
                        None
                    )

                    with yt_dlp.YoutubeDL(
                        fallback
                    ) as ydl:

                        info = ydl.extract_info(
                            target,
                            download=False
                        )

                    return info

                except Exception as e2:

                    print(
                        "[MUSIC] [FALLBACK RESOLVE ERROR]:",
                        repr(e2)
                    )

                    return None

        try:

            info = await loop.run_in_executor(
                None,
                extract
            )

        except Exception as e:

            print(
                "[MUSIC] [RESOLVE EXECUTOR ERROR]:",
                repr(e)
            )

            return None

        if not info:
            return None

        if info.get("entries"):

            entries = [
                x
                for x in (
                    info.get("entries")
                    or []
                )
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

        title = info.get(
            "title",
            "Unknown Song"
        )

        print(
            "[MUSIC] [OK] Selected:",
            title
        )

        return Song(
            title,
            url,
            info.get("thumbnail"),
            requester,
            info.get("duration", 0)
        )


# ============================================================
# AUDIO STREAM
# ============================================================

    async def get_audio_stream(
        self,
        song
    ):

        if (
            song.stream_url
            and
            time.monotonic()
            -
            song.stream_time
            < 240
        ):

            return song.stream_url

        loop = asyncio.get_running_loop()

        def extract():

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

            try:

                with yt_dlp.YoutubeDL(
                    options
                ) as ydl:

                    info = ydl.extract_info(
                        song.url,
                        download=False
                    )

                return info

            except Exception as e:

                print(
                    "[MUSIC] [STREAM PRIMARY ERROR]:",
                    repr(e)
                )

                try:

                    options.pop(
                        "cookiefile",
                        None
                    )

                    with yt_dlp.YoutubeDL(
                        options
                    ) as ydl:

                        return ydl.extract_info(
                            song.url,
                            download=False
                        )

                except Exception as e2:

                    print(
                        "[MUSIC] [STREAM FALLBACK ERROR]:",
                        repr(e2)
                    )

                    return None

        try:

            info = await loop.run_in_executor(
                None,
                extract
            )

        except Exception as e:

            print(
                "[MUSIC] [STREAM EXECUTOR ERROR]:",
                repr(e)
            )

            return None

        if not info:
            return None

        if info.get("entries"):

            entries = [
                x
                for x in (
                    info.get("entries")
                    or []
                )
                if x
            ]

            if not entries:
                return None

            info = entries[0]

        stream_url = info.get("url")

        if not stream_url:
            return None

        song.stream_url = stream_url

        song.stream_time = time.monotonic()

        if not song.thumbnail:

            song.thumbnail = info.get(
                "thumbnail"
            )

        print(
            "[MUSIC] [OK] Fresh stream:",
            song.title
        )

        return stream_url


# ============================================================
# VOICE STATUS
# ============================================================

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
                "[MUSIC] [WARN] Status:",
                repr(e)
            )


# ============================================================
# CLEAR STATUS
# ============================================================

    async def clear_voice_status(self):

        await self.update_voice_status("")


# ============================================================
# STATUS ANIMATION
# ============================================================

    async def start_status_animation(self):

        await self.stop_status_animation(
            clear_status=False
        )

        if not self.voice_channel:
            return

        self.status_task = asyncio.create_task(
            self.status_loop()
        )


    async def status_loop(self):

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
                    %
                    len(DISK_FRAMES)
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


# ============================================================
# AUTOPLAY RELATED SONG ENGINE (FIXED)
# ============================================================

    async def resolve_autoplay_song(self):

        if not self.current:
            return None

        current = self.current

        previous_url = current.url

        previous_title = normalize_title(
            current.title
        )

        requester = current.requester

        base_title = current.title.strip()

        # Artist Extraction (e.g. "Maanu, Hassan & Roshaan - Jhol" -> Artist: Maanu, Hassan & Roshaan)
        artist_match = re.split(r"\s*-\s*", base_title, maxsplit=1)
        artist_name = artist_match[0] if len(artist_match) > 1 else ""

        # Broad Recommendation Queries to prevent repeating the same song keyword
        search_queries = []
        if artist_name:
            search_queries.append(f"{artist_name} songs")
            search_queries.append(f"{artist_name} mix")
        
        search_queries.extend([
            f"songs like {base_title}",
            f"{base_title} radio playlist",
            f"top hindi indie trending songs"
        ])

        seen_urls = set()
        candidates = []

        for search_query in search_queries:

            print(
                "[MUSIC] [AUTOPLAY SEARCH]:",
                search_query
            )

            entries = await self.youtube_search(
                search_query,
                6
            )

            for entry in entries:

                if not entry:
                    continue

                title = str(
                    entry.get("title", "")
                ).strip()

                if not title:
                    continue

                url = (
                    entry.get("webpage_url")
                    or entry.get("original_url")
                )

                video_id = entry.get("id")

                if not url and video_id:
                    url = f"https://www.youtube.com/watch?v={video_id}"

                if not url:
                    continue

                if url == previous_url or url in self.autoplay_history or url in seen_urls:
                    continue

                normalized = normalize_title(title)

                # Skip same song / same title duplicates
                if normalized == previous_title:
                    continue

                if "youtube.com" not in url and "youtu.be" not in url:
                    continue

                lowered = title.lower()

                bad_words = [
                    "shorts",
                    "#shorts",
                    "status",
                    "teaser",
                    "trailer",
                    "cover",
                    "reaction"
                ]

                if any(bad in lowered for bad in bad_words):
                    continue

                seen_urls.add(url)
                candidates.append((url, title, entry))

        if not candidates:
            return None

        # Pick randomly from valid candidates to maintain variance
        selected_url, selected_title, selected_entry = random.choice(candidates)

        self.autoplay_history.append(selected_url)

        return Song(
            selected_title,
            selected_url,
            selected_entry.get("thumbnail"),
            requester,
            selected_entry.get("duration", 0)
        )