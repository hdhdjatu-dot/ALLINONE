import asyncio
import os
import shutil
import ctypes
import ctypes.util
from collections import deque

import discord
import discord.opus
from discord.ext import commands
import yt_dlp


# =========================================================
# HSL-CORP FAST MUSIC SYSTEM
# =========================================================


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
        r"C:\Program Files\opus\bin\opus.dll",
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
            print(
                f"[MUSIC] ⚠️ Opus load failed "
                f"{path}: {e}"
            )

    print("[MUSIC] ❌ Opus codec NOT loaded.")
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
        f"[MUSIC] 🍪 Cookies found: "
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
            "[MUSIC] 🍪 Cookies loaded from ENV."
        )

    except Exception as e:

        print(
            "[MUSIC] ❌ Cookie error:",
            repr(e)
        )


else:

    print(
        "[MUSIC] ⚠️ No YouTube cookies."
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
            f"[MUSIC] ✅ FFmpeg: {ffmpeg}"
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
                f"[MUSIC] ✅ FFmpeg: {path}"
            )

            return path

    print(
        "[MUSIC] ⚠️ FFmpeg not found. "
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

    "format":
        "bestaudio[ext=webm]/"
        "bestaudio[ext=m4a]/"
        "bestaudio/best",

    "http_headers": {

        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
    }
}


if COOKIE_FILE:

    YTDLP_OPTIONS["cookiefile"] = COOKIE_FILE


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
        requester
    ):

        self.title = title

        self.url = url

        self.stream_url = stream_url

        self.thumbnail = thumbnail

        self.duration = duration or 0

        self.requester = requester


# =========================================================
# DURATION FORMAT
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
# MUSIC PLAYER
# =========================================================

class MusicPlayer:

    def __init__(
        self,
        bot
    ):

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

        self.now_playing_message = None


    # =====================================================
    # RESOLVE + STREAM
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
                    "[MUSIC] 🔎 Search:",
                    query
                )

            else:

                print(
                    "[MUSIC] 🔗 URL:",
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

            webpage_url = (
                info.get("webpage_url")
                or info.get("original_url")
                or query
            )


            if not stream_url:

                return None


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
                    )
            }


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
            f"[MUSIC] ✅ {data['title']} "
            f"[{format_duration(data['duration'])}]"
        )


        return Song(

            data["title"],

            data["url"],

            data["stream_url"],

            data["thumbnail"],

            data["duration"],

            requester
        )


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

            # -------------------------------------------------
            # LOOP
            # -------------------------------------------------

            if self.loop and self.current:

                song = self.current


            # -------------------------------------------------
            # QUEUE
            # -------------------------------------------------

            elif self.queue:

                song = self.queue.popleft()

                self.current = song


            # -------------------------------------------------
            # AUTOPLAY
            # -------------------------------------------------

            elif self.autoplay and self.current:

                print(
                    "[MUSIC] 🤖 Autoplay..."
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

                return


            # -------------------------------------------------
            # STREAM
            # -------------------------------------------------

            stream_url = song.stream_url


            if not stream_url:

                print(
                    "[MUSIC] ❌ No stream URL."
                )

                self.current = None

                return


            # -------------------------------------------------
            # STOP OLD
            # -------------------------------------------------

            if (
                self.voice.is_playing()
                or self.voice.is_paused()
            ):

                self.voice.stop()


            # -------------------------------------------------
            # FFMPEG
            # -------------------------------------------------

            before_options = (
                "-reconnect 1 "
                "-reconnect_streamed 1 "
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


            # -------------------------------------------------
            # TOKEN
            # -------------------------------------------------

            self.play_token += 1

            token = self.play_token


            # -------------------------------------------------
            # CALLBACK
            # -------------------------------------------------

            def after_play(error):

                if error:

                    print(
                        "[MUSIC] ❌ Playback:",
                        repr(error)
                    )


                try:

                    asyncio.run_coroutine_threadsafe(

                        self.finished(
                            token
                        ),

                        self.bot.loop
                    )

                except Exception as e:

                    print(
                        "[MUSIC] ❌ Callback:",
                        repr(e)
                    )


            # -------------------------------------------------
            # START IMMEDIATELY
            # -------------------------------------------------

            self.voice.play(

                source,

                after=after_play
            )


            print(
                "[MUSIC] ▶️ NOW PLAYING:",
                song.title
            )

            print(
                "[MUSIC] ⏱️ Duration:",
                format_duration(
                    song.duration
                )
            )


            await self.send_now_playing()


        except Exception as e:

            print(
                "[MUSIC] ❌ PLAY ERROR:",
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
                "[MUSIC] ❌ NOW PLAYING ERROR:",
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
        interaction,
        button
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
        interaction,
        button
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
        interaction,
        button
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
        interaction,
        button
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
        interaction,
        button
    ):

        await interaction.response.defer()


        self.player.play_token += 1

        self.player.queue.clear()

        self.player.current = None

        self.player.starting = False


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


        player = self.get_player(
            ctx.guild.id
        )


        player.text_channel = ctx.channel


        voice_channel = (
            ctx.author.voice.channel
        )


        # -------------------------------------------------
        # CONNECT
        # -------------------------------------------------

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

                    await voice_channel.connect(
                        reconnect=True
                    )
                )


        except Exception as e:

            print(
                "[MUSIC] ❌ VOICE ERROR:",
                repr(e)
            )


            return await ctx.send(

                "❌ Failed to connect "
                "to voice channel.",

                delete_after=5
            )


        # -------------------------------------------------
        # LOADING
        # -------------------------------------------------

        loading = await ctx.send(
            "⚡ **Finding song...**"
        )


        # -------------------------------------------------
        # RESOLVE + STREAM IN ONE STEP
        # -------------------------------------------------

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


        # -------------------------------------------------
        # CHECK CURRENT
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


        player.queue.append(
            song
        )


        print(
            f"[MUSIC] ➕ Queue: "
            f"{song.title} "
            f"[{format_duration(song.duration)}]"
        )


        # -------------------------------------------------
        # QUEUED
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

                    f"⏱️ Duration: "
                    f"`{format_duration(song.duration)}`\n"

                    f"👤 {ctx.author.mention}\n"

                    f"📍 Position: "
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


        # -------------------------------------------------
        # START IMMEDIATELY
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


        player.play_token += 1

        player.queue.clear()

        player.current = None

        player.starting = False


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


        await ctx.send(
            embed=embed
        )


    # =====================================================
    # NOW PLAYING COMMAND
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

                "📭 **Nothing is playing.**",

                delete_after=4
            )


        song = player.current


        embed = discord.Embed(

            title="🎵 NOW PLAYING",

            description=(

                f"**[{song.title}]"
                f"({song.url})**\n\n"

                f"⏱️ Duration: "
                f"`{format_duration(song.duration)}`\n"

                f"👤 Requested by: "
                f"{song.requester.mention}"
            ),

            color=discord.Color.blurple()
        )


        if song.thumbnail:

            embed.set_image(
                url=song.thumbnail
            )


        await ctx.send(
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