
import asyncio
import os
import shutil
from collections import deque

import discord
from discord.ext import commands
import yt_dlp


# =========================================================
# YOUTUBE COOKIES - RAILWAY
# =========================================================

YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES")

COOKIE_FILE = None

if YOUTUBE_COOKIES:

    COOKIE_FILE = "/tmp/youtube_cookies.txt"

    try:

        with open(
            COOKIE_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(YOUTUBE_COOKIES)

        print("[MUSIC] YouTube cookies file created.")
        print(f"[MUSIC] Cookie file: {COOKIE_FILE}")

    except Exception as e:

        print(
            "[MUSIC] Cookie file creation error:",
            repr(e)
        )

else:

    print(
        "[MUSIC] WARNING: YOUTUBE_COOKIES variable is missing."
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
# FIND FFMPEG
# =========================================================

def find_ffmpeg():

    ffmpeg = shutil.which("ffmpeg")

    if ffmpeg:

        print(
            f"[MUSIC] FFmpeg found: {ffmpeg}"
        )

        return ffmpeg

    possible_paths = [

        r"C:\ffmpeg\bin\ffmpeg.exe",

        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",

        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",

    ]

    for path in possible_paths:

        if os.path.isfile(path):

            print(
                f"[MUSIC] FFmpeg found: {path}"
            )

            return path

    print(
        "[MUSIC] WARNING: FFmpeg was not found."
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

    "http_headers": {

        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"

    },

    "extractor_args": {

        "youtube": {

            "player_client": [
                "web",
                "android"
            ]

        }

    }

}


# =========================================================
# APPLY COOKIES
# =========================================================

if (
    COOKIE_FILE
    and os.path.isfile(COOKIE_FILE)
):

    YTDLP_OPTIONS["cookiefile"] = COOKIE_FILE

    print(
        "[MUSIC] yt-dlp cookiefile enabled."
    )

else:

    print(
        "[MUSIC] yt-dlp cookiefile NOT enabled."
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

        self.now_playing_message = None


    # =====================================================
    # RESOLVE SONG
    # =====================================================

    async def resolve_song(
        self,
        query,
        requester
    ):

        loop = asyncio.get_running_loop()

        def extract():

            options = dict(
                YTDLP_OPTIONS
            )

            options["skip_download"] = True

            query = query.strip()

            # ---------------------------------------------
            # DIRECT URL
            # ---------------------------------------------

            if query.startswith(
                (
                    "http://",
                    "https://"
                )
            ):

                target = query

                print(
                    "[MUSIC] Direct URL detected:"
                )

                print(
                    target
                )

            # ---------------------------------------------
            # SEARCH
            # ---------------------------------------------

            else:

                target = (
                    f"ytsearch1:{query}"
                )

                print(
                    f"[MUSIC] Searching YouTube: {query}"
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

                if "entries" in info:

                    entries = [
                        entry
                        for entry in info["entries"]
                        if entry
                    ]

                    if not entries:

                        return None

                    info = entries[0]

                return {

                    "title":
                        info.get(
                            "title",
                            "Unknown Song"
                        ),

                    "url":
                        (
                            info.get(
                                "webpage_url"
                            )
                            or
                            info.get(
                                "original_url"
                            )
                            or
                            query
                        ),

                    "thumbnail":
                        info.get(
                            "thumbnail"
                        )

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

        print(
            f"[MUSIC] Selected: {data['title']}"
        )

        print(
            f"[MUSIC] URL: {data['url']}"
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

            options = dict(
                YTDLP_OPTIONS
            )

            options.update({

                "skip_download": True,

                "format":
                    "bestaudio[ext=webm]/"
                    "bestaudio[ext=m4a]/"
                    "bestaudio/best"

            })

            print(
                "[MUSIC] Extracting fresh audio stream..."
            )

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

                    raise RuntimeError(
                        "No audio stream URL returned."
                    )

                return stream_url

        try:

            stream = await loop.run_in_executor(
                None,
                extract
            )

            if stream:

                print(
                    "[MUSIC] Audio stream obtained successfully."
                )

            return stream

        except Exception as e:

            print(
                "[MUSIC] AUDIO EXTRACTION ERROR:",
                repr(e)
            )

            return None


    # =====================================================
    # PLAY NEXT
    # =====================================================

    async def play_next(self):

        print(
            "[MUSIC] play_next() called"
        )

        if not self.voice:

            print(
                "[MUSIC] No voice client."
            )

            return

        if not self.voice.is_connected():

            print(
                "[MUSIC] Voice client disconnected."
            )

            return

        if self.starting:

            print(
                "[MUSIC] Already starting."
            )

            return

        self.starting = True

        try:

            # ---------------------------------------------
            # LOOP
            # ---------------------------------------------

            if (
                self.loop
                and self.current
            ):

                song = self.current

                print(
                    "[MUSIC] Looping current song."
                )

            # ---------------------------------------------
            # QUEUE
            # ---------------------------------------------

            elif self.queue:

                song = self.queue.popleft()

                self.current = song

                print(
                    f"[MUSIC] Queue selected: {song.title}"
                )

            # ---------------------------------------------
            # AUTOPLAY
            # ---------------------------------------------

            elif (
                self.autoplay
                and self.current
            ):

                print(
                    "[MUSIC] Autoplay: searching related song..."
                )

                query = self.current.title

                song = await self.resolve_song(
                    query,
                    self.current.requester
                )

                if not song:

                    print(
                        "[MUSIC] Autoplay failed."
                    )

                    self.current = None

                    return

                self.current = song

            # ---------------------------------------------
            # NOTHING
            # ---------------------------------------------

            else:

                self.current = None

                print(
                    "[MUSIC] Queue empty."
                )

                return

            print(
                f"[MUSIC] Preparing: {song.title}"
            )

            # ---------------------------------------------
            # AUDIO STREAM
            # ---------------------------------------------

            stream_url = await self.get_audio_stream(
                song
            )

            if not stream_url:

                print(
                    "[MUSIC] No stream URL."
                )

                self.current = None

                return

            # ---------------------------------------------
            # STOP OLD SOURCE
            # ---------------------------------------------

            if (
                self.voice.is_playing()
                or self.voice.is_paused()
            ):

                self.voice.stop()

                await asyncio.sleep(
                    0.3
                )

            # ---------------------------------------------
            # FFMPEG
            # ---------------------------------------------

            before_options = (
                "-reconnect 1 "
                "-reconnect_streamed 1 "
                "-reconnect_delay_max 10 "
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

            # ---------------------------------------------
            # TOKEN
            # ---------------------------------------------

            self.play_token += 1

            token = self.play_token

            # ---------------------------------------------
            # CALLBACK
            # ---------------------------------------------

            def after_play(error):

                if error:

                    print(
                        "[MUSIC] Playback callback error:",
                        repr(error)
                    )

                try:

                    asyncio.run_coroutine_threadsafe(

                        self.finished(token),

                        self.bot.loop

                    )

                except Exception as e:

                    print(
                        "[MUSIC] Callback error:",
                        repr(e)
                    )

            # ---------------------------------------------
            # START
            # ---------------------------------------------

            print(
                "[MUSIC] Starting FFmpeg playback..."
            )

            self.voice.play(
                source,
                after=after_play
            )

            print(
                f"[MUSIC] NOW PLAYING: {song.title}"
            )

            await self.send_now_playing()

        except Exception as e:

            print(
                "[MUSIC] PLAYBACK ERROR:",
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

        print(
            "[MUSIC] Song finished."
        )

        await asyncio.sleep(
            0.7
        )

        if (
            self.voice
            and self.voice.is_connected()
        ):

            await self.play_next()


    # =====================================================
    # NOW PLAYING EMBED
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
                "[MUSIC] EMBED ERROR:",
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

        self.player.play_token += 1

        if (
            self.player.voice.is_playing()
            or self.player.voice.is_paused()
        ):

            self.player.voice.stop()

        self.player.starting = False

        self.player.current = None

        await asyncio.sleep(
            0.4
        )

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

            else

            "🔴 OFF"

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

            else

            "🔴 OFF"

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

                content="⏹️ **Music stopped & queue cleared.**",

                embed=None,

                view=None

            )

        except Exception:

            pass


# =========================================================
# MUSIC COG
# =========================================================

class Music(commands.Cog):

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

            self.players[guild_id] = MusicPlayer(
                self.bot
            )

        return self.players[guild_id]


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

        player.text_channel = ctx.channel

        voice_channel = (
            ctx.author.voice.channel
        )

        # ---------------------------------------------
        # CONNECT
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
                "[MUSIC] VOICE CONNECTION ERROR:",
                repr(e)
            )

            return await ctx.send(

                "❌ Failed to connect to the voice channel.",

                delete_after=5

            )

        # ---------------------------------------------
        # RESOLVE
        # ---------------------------------------------

        loading = await ctx.send(
            "🔎 **Loading song...**"
        )

        song = await player.resolve_song(

            query,

            ctx.author

        )

        if not song:

            return await loading.edit(

                content="❌ Song not found."

            )

        try:

            await loading.delete()

        except Exception:

            pass

        # ---------------------------------------------
        # CHECK CURRENT PLAYBACK
        # ---------------------------------------------

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

            or

            player.current is not None

        )

        # ---------------------------------------------
        # ADD QUEUE
        # ---------------------------------------------

        player.queue.append(
            song
        )

        print(
            f"[MUSIC] Added to queue: {song.title}"
        )

        # ---------------------------------------------
        # ALREADY PLAYING
        # ---------------------------------------------

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

        # ---------------------------------------------
        # START
        # ---------------------------------------------

        await player.play_next()

        await asyncio.sleep(
            1
        )

        if (
            player.voice
            and not player.voice.is_playing()
            and not player.starting
        ):

            print(
                "[MUSIC] WARNING: Audio failed to start."
            )

            await ctx.send(

                "❌ **Audio failed to start.**",

                delete_after=6

            )


    # =====================================================
    # SKIP COMMAND
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

        await asyncio.sleep(
            0.4
        )

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
        description="Stop music and clear queue"
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

                f"`{index}.` "
                f"**{song.title[:70]}**"

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

        if (
            amount < 0
            or amount > 200
        ):

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
        description="Toggle music loop"
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

            else

            "🔴 OFF"

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

            else

            "🔴 OFF"

        )

        await ctx.send(

            f"🤖 **Autoplay: {status}**",

            delete_after=4

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

