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

    "js_runtimes": {
        "deno": {}
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

    "socket_timeout": 20,

    "retries": 3,

    "fragment_retries": 3,

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

        # Voice client
        self.voice = None

        # Channel where music messages belong
        self.text_channel = None

        # Queue
        self.queue = deque()

        # Current song
        self.current = None

        # Volume
        self.volume = 1.0

        # Controls
        self.loop = False
        self.autoplay = True

        # Playback state
        self.starting = False

        self.play_token = 0

        # Prevent two play_next() calls at once
        self.play_lock = asyncio.Lock()

        # Prevent multiple skip commands at once
        self.skip_lock = asyncio.Lock()

        # Now Playing
        self.now_playing_message = None

        # Play command duplicate protection
        self.last_play_request = None
        self.last_play_request_time = 0.0

        # Autoplay history
        self.autoplay_history = deque(
            maxlen=30
        )

        # Manual history
        self.play_history = deque(
            maxlen=30
        )

        # Last manual query
        self.last_manual_query = None

        # Prevent stop/skip transition races
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
                        "status":
                            str(text)[:500]
                    }
                ) as response:

                    if response.status in (
                        200,
                        204
                    ):

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

                    if response.status in (
                        200,
                        204
                    ):

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
            YTDLP_OPTIONS[
                "http_headers"
            ]
        )

        options["js_runtimes"] = {
            "deno": {}
        }

        options["remote_components"] = [
            "ejs:github"
        ]

        if (
            use_cookies
            and COOKIE_FILE
            and os.path.isfile(COOKIE_FILE)
        ):

            options["cookiefile"] = (
                COOKIE_FILE
            )

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

                options = (
                    self.get_ytdlp_options(
                        use_cookies=bool(
                            COOKIE_FILE
                        )
                    )
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
                        for entry
                        in (
                            info.get("entries")
                            or []
                        )
                        if entry
                    ]

                    if not entries:
                        return None

                    info = entries[0]

                webpage_url = (
                    info.get(
                        "webpage_url"
                    )
                    or info.get(
                        "original_url"
                    )
                )

                if not webpage_url:

                    video_id = info.get(
                        "id"
                    )

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
                        info.get(
                            "thumbnail"
                        ),
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

                options = (
                    self.get_ytdlp_options(
                        use_cookies=bool(
                            COOKIE_FILE
                        )
                    )
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
                        for entry
                        in (
                            info.get("entries")
                            or []
                        )
                        if entry
                    ]

                    if not entries:
                        return None

                    info = entries[0]

                stream_url = info.get(
                    "url"
                )

                if stream_url:

                    print(
                        "[MUSIC] [OK] "
                        "Fresh audio stream obtained."
                    )

                    return stream_url

                return None

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
    # AUTOPLAY
    # =====================================================

    async def resolve_autoplay_song(
        self
    ):

        if not self.current:
            return None

        loop = asyncio.get_running_loop()

        requester = (
            self.current.requester
        )

        previous_url = (
            self.current.url
        )

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

        # Also avoid songs recently manually played.
        recent_urls = set(
            self.play_history
        )

        def extract():

            options = (
                self.get_ytdlp_options(
                    use_cookies=bool(
                        COOKIE_FILE
                    )
                )
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

                        # Never current
                        if url == previous_url:
                            continue

                        # Never same title
                        if (
                            title.lower()
                            == previous_title
                        ):
                            continue

                        # Never recent autoplay
                        if url in history_urls:
                            continue

                        # Never recently manually played
                        if url in recent_urls:
                            continue

                        if (
                            "youtube.com"
                            not in url
                            and
                            "youtu.be"
                            not in url
                        ):
                            continue

                        valid.append(
                            entry
                        )

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

                        video_id = (
                            entry.get("id")
                        )

                        if (
                            not url
                            and video_id
                        ):

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

    async def play_next(
        self
    ):

        async with self.play_lock:

            if not self.voice or not self.voice.is_connected():
                self.starting = False
                return

            if self.starting:
                return

            self.starting = True

            try:

                # -----------------------------------------
                # PLAY SELECTION LOOP
                # -----------------------------------------

                while True:

                    if not self.voice or not self.voice.is_connected():
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

                        song = (
                            self.queue.popleft()
                        )

                        self.current = song

                        self.play_history.append(
                            song.url
                        )

                    elif (
                        self.autoplay
                        and self.current
                    ):

                        print(
                            "[MUSIC] "
                            "[AUTOPLAY] Searching..."
                        )

                        song = (
                            await
                            self.resolve_autoplay_song()
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
                    # NEW PLAYBACK TOKEN
                    # -------------------------------------

                    self.play_token += 1

                    token = (
                        self.play_token
                    )

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

                        await asyncio.sleep(
                            0.08
                        )

                    # -------------------------------------
                    # GET FRESH STREAM
                    # -------------------------------------

                    stream_url = (
                        await
                        self.get_audio_stream(
                            song
                        )
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

                    if not stream_url:

                        print(
                            "[MUSIC] [ERROR] "
                            "Stream unavailable:",
                            song.title
                        )

                        if self.queue:

                            print(
                                "[MUSIC] [SKIP FAILED] "
                                "Trying next queued song."
                            )

                            self.current = None

                            continue

                        if self.autoplay:

                            print(
                                "[MUSIC] [AUTOPLAY RETRY] "
                                "Trying another song."
                            )

                            continue

                        self.current = None

                        await self.clear_voice_status()

                        return

                    # -------------------------------------
                    # FFMPEG
                    # -------------------------------------

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

                        # Threadsafe execution to advance queue
                        def advance():
                            if token == self.play_token and not self.stopping:
                                asyncio.create_task(self.play_next())

                        self.bot.loop.call_soon_threadsafe(advance)

                    self.voice.play(source, after=after_play)

                    # Update Voice Status & Text Channel Notice
                    await self.update_voice_status(f"🎶 {song.title}")

                    if self.text_channel:
                        embed = discord.Embed(
                            title="Now Playing",
                            description=f"[{song.title}]({song.url})",
                            color=discord.Color.blue()
                        )
                        if song.thumbnail:
                            embed.set_thumbnail(url=song.thumbnail)
                        embed.set_footer(text=f"Requested by {song.requester.display_name}")
                        
                        try:
                            await self.text_channel.send(embed=embed)
                        except Exception:
                            pass

                    break

            finally:
                self.starting = False


# =========================================================
# BOT DEFINITION & COMMANDS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

players = {}

def get_player(ctx):
    if ctx.guild.id not in players:
        players[ctx.guild.id] = MusicPlayer(bot)
    return players[ctx.guild.id]


@bot.event
async def on_ready():
    print(f"[BOT] [OK] Logged in as {bot.user} (ID: {bot.user.id})")


@bot.command(name="play", aliases=["p"])
async def play(ctx, *, query: str):
    """Play a song from YouTube or direct URL."""
    if not ctx.author.voice:
        return await ctx.send("❌ You must be in a voice channel to use this command!")

    player = get_player(ctx)
    player.text_channel = ctx.channel

    if not ctx.voice_client:
        player.voice = await ctx.author.voice.channel.connect()
    else:
        player.voice = ctx.voice_client

    async with ctx.typing():
        song = await player.resolve_song(query, ctx.author)

        if not song:
            return await ctx.send("❌ Could not resolve song from query!")

        player.queue.append(song)
        await ctx.send(f"🎵 Added **{song.title}** to the queue!")

        if not player.voice.is_playing() and not player.voice.is_paused():
            await player.play_next()


@bot.command(name="skip", aliases=["s"])
async def skip(ctx):
    """Skip the current song."""
    player = get_player(ctx)
    if not player.voice or not player.voice.is_connected():
        return await ctx.send("❌ Not connected to a voice channel.")

    async with player.skip_lock:
        player.invalidate_playback()
        if player.voice.is_playing() or player.voice.is_paused():
            player.voice.stop()
        await ctx.send("⏭️ Skipped current track.")
        await player.play_next()


@bot.command(name="pause")
async def pause(ctx):
    """Pause playback."""
    player = get_player(ctx)
    if player.voice and player.voice.is_playing():
        player.voice.pause()
        await ctx.send("⏸️ Paused playback.")


@bot.command(name="resume")
async def resume(ctx):
    """Resume playback."""
    player = get_player(ctx)
    if player.voice and player.voice.is_paused():
        player.voice.resume()
        await ctx.send("▶️ Resumed playback.")


@bot.command(name="stop")
async def stop(ctx):
    """Stop playing and clear queue."""
    player = get_player(ctx)
    player.stopping = True
    player.invalidate_playback()
    player.queue.clear()
    player.current = None

    if player.voice:
        if player.voice.is_playing() or player.voice.is_paused():
            player.voice.stop()
        await player.clear_voice_status()

    player.stopping = False
    await ctx.send("⏹️ Stopped playback and cleared the queue.")


@bot.command(name="queue", aliases=["q"])
async def queue_info(ctx):
    """Displays queued tracks."""
    player = get_player(ctx)

    if not player.current and not player.queue:
        return await ctx.send("📂 Queue is empty!")

    embed = discord.Embed(title="Current Music Queue", color=discord.Color.purple())

    if player.current:
        embed.add_field(name="Now Playing", value=f"[{player.current.title}]({player.current.url})", inline=False)

    if player.queue:
        queue_list = "\n".join([f"`{i+1}.` [{s.title}]({s.url})" for i, s in enumerate(list(player.queue)[:10])])
        embed.add_field(name="Up Next", value=queue_list, inline=False)

    await ctx.send(embed=embed)


@bot.command(name="volume")
async def volume(ctx, vol: int):
    """Set playback volume (1-100)."""
    if not 0 <= vol <= 100:
        return await ctx.send("❌ Please enter a volume between 0 and 100.")

    player = get_player(ctx)
    player.volume = vol / 100.0

    if player.voice and player.voice.source:
        player.voice.source.volume = player.volume

    await ctx.send(f"🔊 Volume set to {vol}%.")


@bot.command(name="loop")
async def loop(ctx):
    """Toggle current song looping."""
    player = get_player(ctx)
    player.loop = not player.loop
    state = "enabled" if player.loop else "disabled"
    await ctx.send(f"🔂 Looping is now **{state}**.")


@bot.command(name="autoplay")
async def autoplay(ctx):
    """Toggle autoplay mode when queue empties."""
    player = get_player(ctx)
    player.autoplay = not player.autoplay
    state = "enabled" if player.autoplay else "disabled"
    await ctx.send(f"📻 Autoplay is now **{state}**.")


@bot.command(name="leave", aliases=["dc"])
async def leave(ctx):
    """Disconnect bot from voice channel."""
    player = get_player(ctx)
    player.stopping = True
    player.invalidate_playback()
    player.queue.clear()

    if player.voice:
        await player.clear_voice_status()
        await player.voice.disconnect()
        player.voice = None

    player.stopping = False
    await ctx.send("👋 Disconnected from voice channel.")


# =========================================================
# RUN BOT
# =========================================================

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("[MUSIC] [ERROR] DISCORD_TOKEN environment variable not set.")