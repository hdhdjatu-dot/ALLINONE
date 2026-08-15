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
) if __file__ else os.getcwd()


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
# YT-DLP BASE OPTIONS
# =========================================================

YTDLP_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "source_address": "0.0.0.0",
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    },
    "socket_timeout": 15,
    "retries": 5,
    "fragment_retries": 5,
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
        self.play_token = 0
        self.play_lock = asyncio.Lock()
        self.skip_lock = asyncio.Lock()
        self.now_playing_message = None
        self.last_play_request = None
        self.last_play_request_time = 0.0
        self.autoplay_history = deque(maxlen=30)
        self.play_history = deque(maxlen=30)
        self.last_manual_query = None
        self.stopping = False

    def invalidate_playback(self):
        self.play_token += 1
        print(f"[MUSIC] [TOKEN] Playback invalidated -> {self.play_token}")
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
                async with session.put(
                    url,
                    headers=headers,
                    json={"status": str(text)[:500]}
                ) as response:
                    if response.status in (200, 204):
                        print(f"[MUSIC] [OK] VC status updated: {text}")
                    else:
                        error = await response.text()
                        print(f"[MUSIC] [WARN] VC status failed ({response.status}): {error}")
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
                async with session.put(
                    url,
                    headers=headers,
                    json={"status": ""}
                ) as response:
                    if response.status in (200, 204):
                        print("[MUSIC] [OK] VC status cleared.")
        except Exception as e:
            print(f"[MUSIC] [WARN] VC status clear error: {e!r}")

    def get_ytdlp_options(self, use_cookies=True):
        options = dict(YTDLP_OPTIONS)
        options["http_headers"] = dict(YTDLP_OPTIONS["http_headers"])

        if use_cookies and COOKIE_FILE and os.path.isfile(COOKIE_FILE):
            options["cookiefile"] = COOKIE_FILE

        return options

    async def resolve_song(self, search_query, requester):
        loop = asyncio.get_running_loop()

        def extract():
            query = str(search_query).strip()
            if not query:
                return None

            if query.startswith(("http://", "https://")):
                target = query
                print("[MUSIC] [URL] Direct URL:", target)
            else:
                target = f"ytsearch1:{query}"
                print("[MUSIC] [SEARCH] Searching:", query)

            try:
                options = self.get_ytdlp_options(use_cookies=bool(COOKIE_FILE))
                options["skip_download"] = True

                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(target, download=False)

                if not info:
                    return None

                if "entries" in info:
                    entries = [entry for entry in (info.get("entries") or []) if entry]
                    if not entries:
                        return None
                    info = entries[0]

                webpage_url = info.get("webpage_url") or info.get("original_url")
                if not webpage_url:
                    video_id = info.get("id")
                    if video_id:
                        webpage_url = f"https://www.youtube.com/watch?v={video_id}"

                if not webpage_url:
                    return None

                return {
                    "title": info.get("title", "Unknown Song"),
                    "url": webpage_url,
                    "thumbnail": info.get("thumbnail"),
                }

            except Exception as e:
                print("[MUSIC] [ERROR] YouTube resolve failed:", repr(e))
                return None

        try:
            data = await loop.run_in_executor(None, extract)
        except Exception as e:
            print(f"[MUSIC] [ERROR] Resolve error: {e!r}")
            return None

        if not data:
            return None

        print("[MUSIC] [OK] Selected:", data["title"])
        return Song(data["title"], data["url"], data["thumbnail"], requester)

    async def get_audio_stream(self, song):
        loop = asyncio.get_running_loop()

        def extract():
            try:
                options = self.get_ytdlp_options(use_cookies=bool(COOKIE_FILE))
                options.update({
                    "skip_download": True,
                    "format": "bestaudio/best",
                    "noplaylist": True,
                })

                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(song.url, download=False)

                if not info:
                    return None

                if "entries" in info:
                    entries = [entry for entry in (info.get("entries") or []) if entry]
                    if not entries:
                        return None
                    info = entries[0]

                stream_url = info.get("url")
                if stream_url:
                    print("[MUSIC] [OK] Fresh audio stream obtained.")
                    return stream_url

                return None

            except Exception as e:
                print("[MUSIC] [ERROR] Audio stream extraction failed:", repr(e))
                return None

        try:
            return await loop.run_in_executor(None, extract)
        except Exception as e:
            print(f"[MUSIC] [ERROR] Audio error: {e!r}")
            return None

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
                        if not title:
                            continue

                        url = entry.get("webpage_url") or entry.get("original_url")
                        video_id = entry.get("id")
                        if not url and video_id:
                            url = f"https://www.youtube.com/watch?v={video_id}"

                        if not url:
                            continue

                        if url == previous_url or title.lower() == previous_title:
                            continue

                        if url in history_urls or url in recent_urls:
                            continue

                        valid.append(entry)

                    if valid:
                        entry = random.choice(valid)
                        url = entry.get("webpage_url") or entry.get("original_url")
                        video_id = entry.get("id")
                        if not url and video_id:
                            url = f"https://www.youtube.com/watch?v={video_id}"

                        return {
                            "title": entry.get("title", "Unknown Song"),
                            "url": url,
                            "thumbnail": entry.get("thumbnail"),
                        }

                except Exception as e:
                    print("[MUSIC] [WARN] Autoplay search failed:", repr(e))

            return None

        try:
            data = await loop.run_in_executor(None, extract)
        except Exception as e:
            print("[MUSIC] [ERROR] Autoplay search error:", repr(e))
            return None

        if not data:
            return None

        print("[MUSIC] [AUTOPLAY] Selected:", data["title"])
        song = Song(data["title"], data["url"], data.get("thumbnail"), requester)
        self.autoplay_history.append(song.url)
        self.play_history.append(song.url)
        return song

    async def play_next(self):
        async with self.play_lock:
            if not self.voice or not self.voice.is_connected():
                self.starting = False
                return

            if self.starting:
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
                        print("[MUSIC] [AUTOPLAY] Searching...")
                        song = await self.resolve_autoplay_song()
                        if not song:
                            print("[MUSIC] [WARN] Autoplay found no song.")
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

                    print(f"[MUSIC] [PREPARE]: {song.title} | token: {token}")

                    if self.voice.is_playing() or self.voice.is_paused():
                        self.voice.stop()
                        await asyncio.sleep(0.1)

                    stream_url = await self.get_audio_stream(song)

                    if token != self.play_token:
                        print("[MUSIC] [WARN] Playback cancelled before FFmpeg start.")
                        return

                    if not stream_url:
                        print(f"[MUSIC] [ERROR] Stream unavailable: {song.title}")
                        if self.queue or self.autoplay:
                            self.current = None
                            continue
                        self.current = None
                        await self.clear_voice_status()
                        return

                    # Optimized FFmpeg reconnect options to prevent skipping mid-song
                    before_options = (
                        "-reconnect 1 "
                        "-reconnect_streamed 1 "
                        "-reconnect_delay_max 5 "
                        "-nostdin"
                    )

                    ffmpeg_options = (
                        "-vn "
                        "-loglevel error "
                        "-ar 48000 "
                        "-ac 2"
                    )

                    try:
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

                        def after_play(error):
                            if error:
                                print(f"[MUSIC] [ERROR] Playback callback error: {repr(error)}")

                            # Schedule play_next safely without blocking loop thread
                            if token == self.play_token and not self.stopping:
                                asyncio.run_coroutine_threadsafe(
                                    self._on_song_end(), self.bot.loop
                                )

                        self.voice.play(source, after=after_play)
                        await self.update_voice_status(f"🎶 {song.title}")
                        print(f"[MUSIC] [PLAYING]: {song.title}")
                        break

                    except Exception as e:
                        print(f"[MUSIC] [ERROR] Voice play exception: {e!r}")
                        self.current = None
                        continue

            finally:
                self.starting = False

    async def _on_song_end(self):
        await asyncio.sleep(0.5)
        await self.play_next()