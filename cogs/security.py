import asyncio
import json
import os
import re
from datetime import timedelta

import discord
from discord.ext import commands


# ============================================================
# HSL-CORP SECURITY
# ============================================================

DATA_FILE = "security_data.json"
GALI_FILE = "gali_data.json"


# ============================================================
# BOT OWNERS
# ============================================================

BOT_OWNER_IDS = {
    1519933809402056805,
    1435943252455981080,
    1517901703263944758,
    1128339001548476426,
}


# ============================================================
# OWNER ROLE IDS
# ============================================================

OWNER_ROLE_IDS = {
    1451197118025826364,
}


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_SETTINGS = {
    "antinuke": True,
    "antibot": True,
    "antilink": True,
    "antimod": True,
    "antispam": True,
    "duplicate": True,
    "antigali": True,

    # IMPORTANT:
    # IDs are stored as integers
    "whitelist_gali": [],
    "whitelist_music": [],
    "whitelist_bots": [],
}


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(filename):
    if not os.path.exists(filename):
        return {}

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except Exception as e:
        print(f"[SECURITY] JSON LOAD ERROR [{filename}]: {e}")
        return {}


def save_json(filename, data):
    try:
        temp_file = filename + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_file, filename)

    except Exception as e:
        print(f"[SECURITY] JSON SAVE ERROR [{filename}]: {e}")


def load_data():
    return load_json(DATA_FILE)


def save_data(data):
    save_json(DATA_FILE, data)


def load_gali_data():
    return load_json(GALI_FILE)


def save_gali_data(data):
    save_json(GALI_FILE, data)


# ============================================================
# SECURITY COG
# ============================================================

class Security(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.data = load_data()
        self.gali_data = load_gali_data()

        # guild_id:user_id -> last message
        self.duplicate_cache = {}

        print("🛡️ HSL-CORP Security loaded")


    # ========================================================
    # SETTINGS
    # ========================================================

    def get_settings(self, guild_id):

        guild_id = str(guild_id)

        if guild_id not in self.data:
            self.data[guild_id] = {}

        settings = self.data[guild_id]

        changed = False

        for key, default in DEFAULT_SETTINGS.items():

            if key not in settings:

                if isinstance(default, list):
                    settings[key] = list(default)
                else:
                    settings[key] = default

                changed = True

        # ----------------------------------------------------
        # Normalize all whitelist IDs
        # ----------------------------------------------------

        for whitelist_name in (
            "whitelist_gali",
            "whitelist_music",
            "whitelist_bots"
        ):

            old = settings.get(
                whitelist_name,
                []
            )

            if not isinstance(old, list):
                old = []
                changed = True

            new = []

            for value in old:
                try:
                    value = int(value)

                    if value > 0:
                        new.append(value)

                except (TypeError, ValueError):
                    changed = True

            new = list(dict.fromkeys(new))

            if new != old:
                settings[whitelist_name] = new
                changed = True

        if changed:
            save_data(self.data)

        return settings


    # ========================================================
    # BOT OWNER
    # ========================================================

    async def is_bot_owner(self, user):

        if user is None:
            return False

        if user.id in BOT_OWNER_IDS:
            return True

        try:
            return await self.bot.is_owner(user)

        except Exception as e:
            print(
                "[SECURITY] BOT OWNER CHECK ERROR:",
                repr(e)
            )

            return False


    # ========================================================
    # OWNER ROLE
    # ========================================================

    def has_owner_role(self, member):

        if not isinstance(member, discord.Member):
            return False

        return any(
            role.id in OWNER_ROLE_IDS
            for role in member.roles
        )


    # ========================================================
    # MASTER OWNER CHECK
    # ========================================================

    async def is_owner(self, member):

        if not isinstance(member, discord.Member):
            return False

        if member.guild is None:
            return False

        # Server owner
        if member.id == member.guild.owner_id:
            return True

        # Bot owner
        if await self.is_bot_owner(member):
            return True

        # Owner role
        if self.has_owner_role(member):
            return True

        return False


    # ========================================================
    # OWNER ERROR
    # ========================================================

    async def owner_only_message(self, ctx):

        try:
            await ctx.send(
                "❌ **Only the Server Owner, Bot Owner, "
                "or configured Owner Role can use this command.**",
                delete_after=5
            )

        except Exception:
            pass


    # ========================================================
    # GALI WORDS
    # ========================================================

    def get_gali_words(self, guild_id):

        guild_id = str(guild_id)

        words = self.gali_data.get(
            guild_id,
            []
        )

        if not isinstance(words, list):
            words = []

        cleaned = []

        for word in words:

            if not isinstance(word, str):
                continue

            word = word.strip().lower()

            if word:
                cleaned.append(word)

        cleaned = list(dict.fromkeys(cleaned))

        if cleaned != words:

            self.gali_data[guild_id] = cleaned
            save_gali_data(self.gali_data)

        return cleaned


    # ========================================================
    # FIND GALI
    # ========================================================

    def find_gali(self, guild_id, content):

        if not content:
            return None

        words = self.get_gali_words(guild_id)

        if not words:
            return None

        content = content.lower()

        # Longest words first
        # Prevents short words from winning
        words = sorted(
            words,
            key=len,
            reverse=True
        )

        for word in words:

            word = word.strip().lower()

            if not word:
                continue

            # Phrase
            if " " in word:

                if word in content:
                    return word

                continue

            # Single word
            pattern = (
                r"(?<!\w)"
                + re.escape(word)
                + r"(?!\w)"
            )

            try:

                if re.search(
                    pattern,
                    content,
                    flags=re.IGNORECASE
                ):
                    return word

            except Exception:
                continue

        return None


    # ========================================================
    # GALI WHITELIST CHECK
    # ========================================================

    def gali_whitelisted(self, guild_id, user_id):

        try:
            guild_id = str(int(guild_id))
            user_id = int(user_id)

        except (TypeError, ValueError):
            return False

        settings = self.get_settings(guild_id)

        whitelist = settings.get(
            "whitelist_gali",
            []
        )

        if not isinstance(whitelist, list):
            return False

        for allowed_id in whitelist:

            try:

                if int(allowed_id) == user_id:
                    return True

            except (TypeError, ValueError):
                continue

        return False


    # ========================================================
    # GALI BYPASS
    # ========================================================

    async def gali_bypass(self, member):

        if not isinstance(member, discord.Member):
            return False

        guild = member.guild

        # ====================================================
        # MOST IMPORTANT CHECK
        # ====================================================
        #
        # Member whitelist ONLY bypasses Anti-Gali.
        #

        if self.gali_whitelisted(
            guild.id,
            member.id
        ):
            return True

        # Server owner
        if member.id == guild.owner_id:
            return True

        # Bot owner
        if member.id in BOT_OWNER_IDS:
            return True

        try:

            if await self.bot.is_owner(member):
                return True

        except Exception:
            pass

        # Owner role
        if self.has_owner_role(member):
            return True

        return False


    # ========================================================
    # MUSIC WHITELIST
    # ========================================================

    def music_whitelisted(self, guild_id, user_id):

        settings = self.get_settings(guild_id)

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return False

        for allowed in settings.get(
            "whitelist_music",
            []
        ):

            try:

                if int(allowed) == user_id:
                    return True

            except (TypeError, ValueError):
                pass

        return False


    # ========================================================
    # MUSIC COMMAND
    # ========================================================

    def is_music_command(self, content):

        if not content:
            return False

        content = content.strip().lower()

        first = content.split(
            maxsplit=1
        )[0]

        return first in (
            "!play",
            "!p",
            "/play",
            "/p"
        )


    # ========================================================
    # SECURITY ANIMATION
    # ========================================================

    async def security_animation(self, ctx, enabled):

        try:

            message = await ctx.send(
                "```ansi\n"
                "\u001b[1;32m"
                "╔══════════════════════════════╗\n"
                "║                              ║\n"
                "║       H S L - C O R P        ║\n"
                "║                              ║\n"
                "║       ◐ INITIALIZING         ║\n"
                "║                              ║\n"
                "║       SECURITY SYSTEM        ║\n"
                "║                              ║\n"
                "╚══════════════════════════════╝\n"
                "\u001b[0m"
                "```"
            )

        except Exception as e:

            print(
                "[SECURITY] ANIMATION SEND ERROR:",
                repr(e)
            )

            return


        spinner = [
            "◐",
            "◓",
            "◑",
            "◒"
        ]

        systems = [
            ("🔗", "ANTI-LINK", "antilink"),
            ("🤖", "ANTI-BOT", "antibot"),
            ("☢️", "ANTI-NUKE", "antinuke"),
            ("🔨", "ANTI-MOD", "antimod"),
            ("💬", "ANTI-SPAM", "antispam"),
            ("♻️", "DUPLICATE GUARD", "duplicate"),
            ("🤬", "ANTI-GALI", "antigali")
        ]

        settings = self.get_settings(
            ctx.guild.id
        )

        for i in range(10):

            frame = spinner[
                i % len(spinner)
            ]

            percentage = min(
                90,
                10 + i * 8
            )

            filled = int(
                percentage / 10
            )

            bar = (
                "█" * filled
                +
                "░" * (10 - filled)
            )

            try:

                await message.edit(
                    content=(
                        "```ansi\n"
                        "\u001b[1;32m"
                        "╔══════════════════════════════╗\n"
                        "║       HSL-CORP SECURITY      ║\n"
                        "╠══════════════════════════════╣\n"
                        "║                              ║\n"
                        f"║       {frame} SYSTEM CHECK      ║\n"
                        "║                              ║\n"
                        f"║       [{bar}] {percentage:>3}% ║\n"
                        "║                              ║\n"
                        "║       ▸ INITIALIZING...      ║\n"
                        "║                              ║\n"
                        "╚══════════════════════════════╝\n"
                        "\u001b[0m"
                        "```"
                    )
                )

            except Exception:
                break

            await asyncio.sleep(0.16)


        completed = []

        for index, (
            emoji,
            name,
            key
        ) in enumerate(systems):

            for frame_index in range(5):

                frame = spinner[
                    frame_index % len(spinner)
                ]

                percent = int(
                    (
                        index
                        +
                        frame_index / 5
                    )
                    / len(systems)
                    * 100
                )

                percent = min(
                    percent,
                    99
                )

                bar_length = 20

                filled = int(
                    percent / 100 * bar_length
                )

                bar = (
                    "█" * filled
                    +
                    "░" * (
                        bar_length - filled
                    )
                )

                old_lines = ""

                for old in completed:

                    old_lines += (
                        f"║   {old[0]} "
                        f"{old[1]:<18} "
                        "✓ READY ║\n"
                    )

                try:

                    await message.edit(
                        content=(
                            "```ansi\n"
                            "\u001b[1;32m"
                            "╔══════════════════════════════╗\n"
                            "║       HSL-CORP SECURITY      ║\n"
                            "╠══════════════════════════════╣\n"
                            f"{old_lines}"
                            "║                              ║\n"
                            f"║   {frame} {emoji} {name:<18} ║\n"
                            "║                              ║\n"
                            f"║   [{bar}] ║\n"
                            f"║             {percent:>3}%            ║\n"
                            "║                              ║\n"
                            "║   ◉ SCANNING SECURITY...     ║\n"
                            "║                              ║\n"
                            "╚══════════════════════════════╝\n"
                            "\u001b[0m"
                            "```"
                        )
                    )

                except Exception:
                    pass

                await asyncio.sleep(0.12)


            settings[key] = enabled
            save_data(self.data)

            completed.append(
                (
                    emoji,
                    name
                )
            )

            await asyncio.sleep(0.25)


        final_text = (
            "SYSTEM ONLINE"
            if enabled
            else
            "SYSTEM OFFLINE"
        )

        try:

            await message.edit(
                content=(
                    "```ansi\n"
                    "\u001b[1;32m"
                    "╔══════════════════════════════╗\n"
                    "║                              ║\n"
                    "║       H S L - C O R P        ║\n"
                    "║                              ║\n"
                    f"║       ◉ {final_text:<17}║\n"
                    "║                              ║\n"
                    "║       ✓ ANTI-LINK            ║\n"
                    "║       ✓ ANTI-BOT             ║\n"
                    "║       ✓ ANTI-NUKE            ║\n"
                    "║       ✓ ANTI-MOD             ║\n"
                    "║       ✓ ANTI-SPAM            ║\n"
                    "║       ✓ DUPLICATE GUARD      ║\n"
                    "║       ✓ ANTI-GALI            ║\n"
                    "║                              ║\n"
                    "║   ████████████████████████   ║\n"
                    "║          100% SECURE         ║\n"
                    "║                              ║\n"
                    "╚══════════════════════════════╝\n"
                    "\u001b[0m"
                    "```"
                )
            )

        except Exception:
            pass

        await asyncio.sleep(5)

        try:
            await message.delete()
        except Exception:
            pass


    # ========================================================
    # ANTINUKE ENABLE
    # ========================================================

    @commands.hybrid_command(
        name="antinukeenable",
        description="Enable HSL-CORP security"
    )
    @commands.guild_only()
    async def antinukeenable(self, ctx):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        await self.security_animation(
            ctx,
            True
        )


    # ========================================================
    # ANTINUKE DISABLE
    # ========================================================

    @commands.hybrid_command(
        name="antinukedisable",
        description="Disable HSL-CORP security"
    )
    @commands.guild_only()
    async def antinukedisable(self, ctx):

        if not await self.is_owner(ctx):
            return await self.owner_only_message(ctx)

        await self.security_animation(
            ctx,
            False
        )


    # ========================================================
    # AUTOMOD STATUS
    # ========================================================

    @commands.hybrid_command(
        name="automodstatus",
        description="Show HSL-CORP security status"
    )
    @commands.guild_only()
    async def automodstatus(self, ctx):

        settings = self.get_settings(
            ctx.guild.id
        )

        def st(key):
            return (
                "🟢 ON"
                if settings.get(key, False)
                else "🔴 OFF"
            )

        embed = discord.Embed(
            title="🛡️ HSL-CORP SECURITY STATUS",
            color=discord.Color.dark_green()
        )

        embed.add_field(
            name="🔗 Anti-Link",
            value=st("antilink"),
            inline=True
        )

        embed.add_field(
            name="🤖 Anti-Bot",
            value=st("antibot"),
            inline=True
        )

        embed.add_field(
            name="☢️ Anti-Nuke",
            value=st("antinuke"),
            inline=True
        )

        embed.add_field(
            name="🔨 Anti-Mod",
            value=st("antimod"),
            inline=True
        )

        embed.add_field(
            name="💬 Anti-Spam",
            value=st("antispam"),
            inline=True
        )

        embed.add_field(
            name="♻️ Duplicate",
            value=st("duplicate"),
            inline=True
        )

        embed.add_field(
            name="🤬 Anti-Gali",
            value=st("antigali"),
            inline=True
        )

        embed.add_field(
            name="🤬 Gali Whitelist",
            value=str(
                len(
                    settings.get(
                        "whitelist_gali",
                        []
                    )
                )
            ),
            inline=True
        )

        await ctx.send(
            embed=embed
        )


    # ========================================================
    # CLEAR
    # ========================================================

    @commands.hybrid_command(
        name="clear",
        description="Delete messages"
    )
    @commands.guild_only()
    async def clear(self, ctx, amount: int):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        if amount < 1 or amount > 100:

            return await ctx.send(
                "❌ Amount `1-100` ke beech hona chahiye.",
                delete_after=5
            )

        try:

            deleted = await ctx.channel.purge(
                limit=amount + 1
            )

            count = len(deleted)

            if ctx.message and ctx.message in deleted:
                count -= 1

            count = max(0, count)

            msg = await ctx.send(
                f"🧹 **{count} messages cleared.**"
            )

            await asyncio.sleep(3)

            try:
                await msg.delete()
            except Exception:
                pass

        except discord.Forbidden:

            await ctx.send(
                "❌ Mujhe messages delete karne ki permission nahi hai.",
                delete_after=5
            )

        except Exception as e:

            print(
                "[SECURITY] CLEAR ERROR:",
                repr(e)
            )


    # ========================================================
    # SAY
    # ========================================================

    @commands.hybrid_command(
        name="say",
        description="Send a message as HSL-CORP"
    )
    @commands.guild_only()
    async def say(self, ctx, *, text: str):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        if not text.strip():

            return await ctx.send(
                "❌ Message empty nahi ho sakta.",
                delete_after=5
            )

        try:

            await ctx.send(
                text.strip(),
                allowed_mentions=discord.AllowedMentions.none()
            )

            if ctx.message:

                try:
                    await ctx.message.delete()
                except Exception:
                    pass

        except Exception as e:

            print(
                "[SECURITY] SAY ERROR:",
                repr(e)
            )


    # ========================================================
    # ADD GALI
    # ========================================================

    @commands.hybrid_command(
        name="addgali",
        description="Add a word to Anti-Gali filter"
    )
    @commands.guild_only()
    async def addgali(self, ctx, *, word: str):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        word = word.strip().lower()
        word = re.sub(r"\s+", " ", word)

        if not word:

            return await ctx.send(
                "❌ Gali word empty nahi ho sakta.",
                delete_after=5
            )

        guild_id = str(ctx.guild.id)

        words = self.get_gali_words(
            ctx.guild.id
        )

        if word in words:

            return await ctx.send(
                f"🟡 `{word}` already list mein hai.",
                delete_after=5
            )

        words.append(word)

        self.gali_data[guild_id] = words

        save_gali_data(
            self.gali_data
        )

        await ctx.send(
            f"🔴 **ANTI-GALI**\n"
            f"`{word}` successfully add kar diya.\n"
            f"Total blocked words: **{len(words)}**",
            delete_after=7
        )


    # ========================================================
    # REMOVE GALI
    # ========================================================

    @commands.hybrid_command(
        name="removegali",
        description="Remove a word from Anti-Gali filter"
    )
    @commands.guild_only()
    async def removegali(self, ctx, *, word: str):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        word = word.strip().lower()

        words = self.get_gali_words(
            ctx.guild.id
        )

        if word not in words:

            return await ctx.send(
                f"🟡 `{word}` list mein nahi hai.",
                delete_after=5
            )

        words.remove(word)

        self.gali_data[str(ctx.guild.id)] = words

        save_gali_data(
            self.gali_data
        )

        await ctx.send(
            f"🟢 `{word}` Anti-Gali list se remove kar diya.",
            delete_after=6
        )


    # ========================================================
    # GALI LIST
    # ========================================================

    @commands.hybrid_command(
        name="galilist",
        description="Show Anti-Gali blocked words"
    )
    @commands.guild_only()
    async def galilist(self, ctx):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        words = self.get_gali_words(
            ctx.guild.id
        )

        if not words:

            return await ctx.send(
                "🟢 Anti-Gali list empty hai.",
                delete_after=6
            )

        display = words[:100]

        description = "\n".join(
            f"`{i}.` `{word}`"
            for i, word in enumerate(
                display,
                1
            )
        )

        embed = discord.Embed(
            title="🤬 HSL-CORP ANTI-GALI",
            description=description,
            color=discord.Color.red()
        )

        embed.add_field(
            name="Blocked Words",
            value=str(len(words)),
            inline=True
        )

        embed.add_field(
            name="Status",
            value="🟢 ENABLED",
            inline=True
        )

        await ctx.send(
            embed=embed
        )


    # ========================================================
    # WHITELIST GALI
    #
    # /whitelistgali @user
    # -> ADD
    #
    # /whitelistgali @user add
    # -> ADD
    #
    # /whitelistgali @user remove
    # -> REMOVE
    #
    # /whitelistgali
    # -> SHOW LIST
    # ========================================================



    # ========================================================
    # WHITELIST BOT
    # ========================================================

    @commands.hybrid_command(
        name="whitelistbot",
        description="Whitelist or remove a bot"
    )
    @commands.guild_only()
    async def whitelistbot(
        self,
        ctx,
        bot_id: str,
        action: str = "add"
    ):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        try:

            clean_id = (
                bot_id
                .strip()
                .replace("<@", "")
                .replace(">", "")
                .replace("!", "")
            )

            uid = int(clean_id)

        except (TypeError, ValueError):

            return await ctx.send(
                "❌ Sahi Bot ID / Mention daalo.",
                delete_after=5
            )

        try:
            user = await self.bot.fetch_user(uid)

        except Exception:

            return await ctx.send(
                "❌ Bot nahi mila.",
                delete_after=5
            )

        if not user.bot:

            return await ctx.send(
                "❌ Ye user bot nahi hai.",
                delete_after=5
            )

        settings = self.get_settings(
            ctx.guild.id
        )

        bots = settings.setdefault(
            "whitelist_bots",
            []
        )

        bots = [
            int(x)
            for x in bots
            if str(x).isdigit()
        ]

        bots = list(
            dict.fromkeys(bots)
        )

        action = action.lower().strip()

        if action in (
            "add",
            "on",
            "enable",
            "toggle"
        ):

            if uid in bots:

                return await ctx.send(
                    f"🟢 {user.mention} "
                    "**already bot whitelist mein hai.**",
                    delete_after=5
                )

            bots.append(uid)

            settings["whitelist_bots"] = bots

            save_data(
                self.data
            )

            return await ctx.send(
                f"🤖 {user.mention} "
                "**bot whitelist mein add ho gaya.**",
                delete_after=7
            )

        if action in (
            "remove",
            "delete",
            "del",
            "off",
            "disable"
        ):

            if uid not in bots:

                return await ctx.send(
                    f"🟡 {user.mention} "
                    "**bot whitelist mein nahi hai.**",
                    delete_after=5
                )

            bots.remove(uid)

            settings["whitelist_bots"] = bots

            save_data(
                self.data
            )

            return await ctx.send(
                f"🔴 {user.mention} "
                "**bot whitelist se remove ho gaya.**",
                delete_after=6
            )

        await ctx.send(
            "❌ Invalid action.",
            delete_after=5
        )


    # ========================================================
    # WHITELIST BOTS LIST
    # ========================================================

    @commands.hybrid_command(
        name="whitelistbots",
        description="Show whitelisted bots"
    )
    @commands.guild_only()
    async def whitelistbots(self, ctx):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        settings = self.get_settings(
            ctx.guild.id
        )

        bots = settings.get(
            "whitelist_bots",
            []
        )

        if not bots:

            return await ctx.send(
                "🤖 **No bots are currently whitelisted.**",
                delete_after=6
            )

        lines = []

        for index, bot_id in enumerate(
            bots,
            1
        ):

            member = ctx.guild.get_member(
                int(bot_id)
            )

            if member:

                lines.append(
                    f"**{index}.** "
                    f"{member.mention} "
                    f"`{member.id}`"
                )

            else:

                lines.append(
                    f"**{index}.** "
                    f"<@{bot_id}> "
                    f"`{bot_id}`"
                )

        embed = discord.Embed(
            title="🤖 HSL-CORP BOT WHITELIST",
            description="\n".join(lines),
            color=discord.Color.green()
        )

        await ctx.send(
            embed=embed
        )


    # ========================================================
    # MUSIC WHITELIST
    # ========================================================

    @commands.hybrid_command(
        name="whitelist",
        description="Manage music whitelist"
    )
    @commands.guild_only()
    async def whitelist(
        self,
        ctx,
        member: discord.Member = None,
        action: str = "toggle"
    ):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        settings = self.get_settings(
            ctx.guild.id
        )

        users = settings.setdefault(
            "whitelist_music",
            []
        )

        users = list(
            dict.fromkeys(
                int(x)
                for x in users
                if str(x).isdigit()
            )
        )

        settings["whitelist_music"] = users

        if member is None:

            if not users:

                return await ctx.send(
                    "🎵 Music whitelist empty hai.",
                    delete_after=6
                )

            lines = []

            for i, uid in enumerate(
                users,
                1
            ):

                m = ctx.guild.get_member(uid)

                if m:
                    lines.append(
                        f"**{i}.** {m.mention} `{m.id}`"
                    )
                else:
                    lines.append(
                        f"**{i}.** <@{uid}> `{uid}`"
                    )

            embed = discord.Embed(
                title="🎵 HSL-CORP MUSIC WHITELIST",
                description="\n".join(lines),
                color=discord.Color.green()
            )

            return await ctx.send(
                embed=embed
            )

        action = action.lower().strip()

        if action in (
            "add",
            "on",
            "enable"
        ):

            if member.id in users:

                return await ctx.send(
                    f"🟢 {member.mention} already whitelisted.",
                    delete_after=5
                )

            users.append(member.id)

            settings["whitelist_music"] = users

            save_data(
                self.data
            )

            return await ctx.send(
                f"🟢 {member.mention} music whitelist mein add ho gaya.",
                delete_after=6
            )

        if action in (
            "remove",
            "delete",
            "del",
            "off",
            "disable"
        ):

            if member.id not in users:

                return await ctx.send(
                    f"🟡 {member.mention} whitelist mein nahi hai.",
                    delete_after=5
                )

            users.remove(member.id)

            settings["whitelist_music"] = users

            save_data(
                self.data
            )

            return await ctx.send(
                f"🔴 {member.mention} music whitelist se remove ho gaya.",
                delete_after=6
            )

        if action == "toggle":

            if member.id in users:
                users.remove(member.id)

                text = (
                    f"🔴 {member.mention} "
                    "music whitelist se remove ho gaya."
                )

            else:
                users.append(member.id)

                text = (
                    f"🟢 {member.mention} "
                    "music whitelist mein add ho gaya."
                )

            settings["whitelist_music"] = list(
                dict.fromkeys(users)
            )

            save_data(
                self.data
            )

            return await ctx.send(
                text,
                delete_after=6
            )

        await ctx.send(
            "❌ Invalid action.",
            delete_after=5
        )


    # ========================================================
    # GIVE ROLE
    # ========================================================

    @commands.command(
        name="giverole"
    )
    @commands.guild_only()
    async def giverole(
        self,
        ctx,
        member: discord.Member,
        role: discord.Role
    ):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        if role.is_default():

            return await ctx.send(
                "❌ @everyone assign nahi kar sakte.",
                delete_after=5
            )

        if role.managed:

            return await ctx.send(
                "❌ Ye managed role hai.",
                delete_after=5
            )

        me = ctx.guild.me

        if not me:

            return await ctx.send(
                "❌ Bot member unavailable.",
                delete_after=5
            )

        if role >= me.top_role:

            return await ctx.send(
                "❌ Ye role bot ke highest role se upar hai.",
                delete_after=5
            )

        try:

            await member.add_roles(
                role,
                reason=f"HSL Security giverole by {ctx.author}"
            )

            await ctx.send(
                f"✅ {role.mention} {member.mention} ko de diya.",
                delete_after=5
            )

        except discord.Forbidden:

            await ctx.send(
                "❌ Role assign karne ki permission nahi hai.",
                delete_after=5
            )

        except Exception as e:

            print(
                "[SECURITY] GIVEROLE ERROR:",
                repr(e)
            )


    # ========================================================
    # REMOVE ROLE
    # ========================================================

    @commands.command(
        name="removerole"
    )
    @commands.guild_only()
    async def removerole(
        self,
        ctx,
        member: discord.Member,
        role: discord.Role
    ):

        if not await self.is_owner(ctx.author):
            return await self.owner_only_message(ctx)

        if role.is_default():

            return await ctx.send(
                "❌ @everyone remove nahi kar sakte.",
                delete_after=5
            )

        if role.managed:

            return await ctx.send(
                "❌ Ye managed role hai.",
                delete_after=5
            )

        me = ctx.guild.me

        if not me:
            return

        if role >= me.top_role:

            return await ctx.send(
                "❌ Ye role bot ke highest role se upar hai.",
                delete_after=5
            )

        if role not in member.roles:

            return await ctx.send(
                f"🟡 {member.mention} ke paas ye role nahi hai.",
                delete_after=5
            )

        try:

            await member.remove_roles(
                role,
                reason=f"HSL Security removerole by {ctx.author}"
            )

            await ctx.send(
                f"✅ {role.mention} {member.mention} se remove kar diya.",
                delete_after=5
            )

        except discord.Forbidden:

            await ctx.send(
                "❌ Role remove karne ki permission nahi hai.",
                delete_after=5
            )

        except Exception as e:

            print(
                "[SECURITY] REMOVEROLE ERROR:",
                repr(e)
            )


    # ========================================================
    # STRICT ANTI-BOT
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(self, member):

        if not member.bot:
            return

        guild = member.guild

        settings = self.get_settings(
            guild.id
        )

        if not settings.get(
            "antibot",
            True
        ):
            return

        whitelist = settings.get(
            "whitelist_bots",
            []
        )

        try:

            if member.id in {
                int(x)
                for x in whitelist
            }:

                print(
                    f"[SECURITY] WHITELISTED BOT ALLOWED: "
                    f"{member} ({member.id})"
                )

                return

        except Exception:
            pass

        inviter = None

        for _ in range(12):

            try:

                await asyncio.sleep(0.75)

                async for entry in guild.audit_logs(
                    limit=50,
                    action=discord.AuditLogAction.bot_add
                ):

                    if not entry.target:
                        continue

                    if entry.target.id != member.id:
                        continue

                    age = (
                        discord.utils.utcnow()
                        - entry.created_at
                    ).total_seconds()

                    if 0 <= age <= 30:

                        inviter = entry.user
                        break

                if inviter:
                    break

            except discord.Forbidden:

                print(
                    "[SECURITY] Cannot read audit logs."
                )

                break

            except Exception as e:

                print(
                    "[SECURITY] Audit error:",
                    repr(e)
                )

        if inviter is None:

            await self.kick_unauthorized_bot(
                member
            )

            return

        # Server owner allowed
        if inviter.id == guild.owner_id:
            return

        inviter_member = guild.get_member(
            inviter.id
        )

        if inviter_member is None:

            try:
                inviter_member = await guild.fetch_member(
                    inviter.id
                )
            except Exception:
                inviter_member = None

        await self.kick_unauthorized_bot(
            member
        )

        if inviter_member:

            await self.remove_inviter_roles(
                inviter_member
            )


    # ========================================================
    # KICK BOT
    # ========================================================

    async def kick_unauthorized_bot(self, member):

        guild = member.guild
        me = guild.me

        if not me:
            return False

        if not me.guild_permissions.kick_members:
            return False

        if self.bot.user and member.id == self.bot.user.id:
            return False

        if member.top_role >= me.top_role:
            return False

        try:

            await member.kick(
                reason="HSL-CORP Security - Unauthorized bot"
            )

            print(
                f"[SECURITY] BOT KICKED: {member}"
            )

            return True

        except Exception as e:

            print(
                "[SECURITY] BOT KICK ERROR:",
                repr(e)
            )

            return False


    # ========================================================
    # REMOVE INVITER ROLES
    # ========================================================

    async def remove_inviter_roles(self, member):

        if not member:
            return

        guild = member.guild

        if member.id == guild.owner_id:
            return

        me = guild.me

        if not me:
            return

        if not me.guild_permissions.manage_roles:
            return

        for role in list(member.roles):

            if role.is_default():
                continue

            if role.managed:
                continue

            if role >= me.top_role:
                continue

            try:

                await member.remove_roles(
                    role,
                    reason=(
                        "HSL-CORP Security - "
                        "Unauthorized bot addition"
                    )
                )

                await asyncio.sleep(0.2)

            except Exception as e:

                print(
                    "[SECURITY] ROLE REMOVE ERROR:",
                    repr(e)
                )


    # ========================================================
    # ANTI-GALI
    #
    # IMPORTANT:
    # This check MUST happen before deleting/timeout.
    # ========================================================

    async def process_gali(self, message):

        if not message.guild:
            return False

        settings = self.get_settings(
            message.guild.id
        )

        if not settings.get(
            "antigali",
            True
        ):
            return False

        # ====================================================
        # HARD WHITELIST CHECK
        # ====================================================

        if self.gali_whitelisted(
            message.guild.id,
            message.author.id
        ):

            print(
                f"[GALI] ✅ WHITELIST BYPASS: "
                f"{message.author} ({message.author.id})"
            )

            return False

        # Server owner
        if message.author.id == message.guild.owner_id:
            return False

        # Bot owner
        if message.author.id in BOT_OWNER_IDS:
            return False

        # Owner role
        if self.has_owner_role(message.author):
            return False

        # discord.py owner
        try:

            if await self.bot.is_owner(
                message.author
            ):
                return False

        except Exception:
            pass

        # ====================================================
        # FIND WORD
        # ====================================================

        detected = self.find_gali(
            message.guild.id,
            message.content or ""
        )

        if not detected:
            return False

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        print(
            "[SECURITY] 🚨 ANTI-GALI DETECTED"
        )

        print(
            f"[SECURITY] User: "
            f"{message.author} ({message.author.id})"
        )

        print(
            f"[SECURITY] Word: {detected}"
        )

        # ====================================================
        # DELETE
        # ====================================================

        try:

            await message.delete()

            print(
                "[GALI] ✅ Message deleted."
            )

        except discord.NotFound:
            pass

        except discord.Forbidden:

            print(
                "[GALI] ❌ Cannot delete message."
            )

        except Exception as e:

            print(
                "[GALI] DELETE ERROR:",
                repr(e)
            )

        # ====================================================
        # TIMEOUT
        # ====================================================

        try:

            # Do not timeout server owner
            if message.author.id != message.guild.owner_id:

                await message.author.timeout(
                    timedelta(minutes=10),
                    reason=(
                        "HSL-CORP Anti-Gali - "
                        "Blocked word"
                    )
                )

        except discord.Forbidden:

            print(
                "[GALI] ❌ Cannot timeout user."
            )

        except Exception as e:

            print(
                "[GALI] TIMEOUT ERROR:",
                repr(e)
            )

        # ====================================================
        # WARNING
        # ====================================================

        try:

            warning = await message.channel.send(
                f"🤬 {message.author.mention} "
                "**gali detected — 10 minute timeout.**",
                allowed_mentions=discord.AllowedMentions(
                    users=True
                )
            )

            await asyncio.sleep(3)

            try:
                await warning.delete()
            except Exception:
                pass

        except Exception:
            pass

        return True


    # ========================================================
    # MESSAGE SECURITY
    # ========================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        # Bots ignored
        if message.author.bot:
            return

        # DMs ignored
        if not message.guild:
            return

        content = (
            message.content or ""
        ).strip()

        lower_content = content.lower()

        settings = self.get_settings(
            message.guild.id
        )

        # ====================================================
        # ANTI-GALI
        # ====================================================

        # IMPORTANT:
        # process_gali() itself checks whitelist.
        #
        # If whitelisted:
        # NOTHING happens here.
        #

        if await self.process_gali(message):
            return

        # ====================================================
        # DUPLICATE
        # ====================================================

        if settings.get(
            "duplicate",
            True
        ):

            key = (
                message.guild.id,
                message.author.id
            )

            old = self.duplicate_cache.get(
                key
            )

            if old == content and content:

                try:
                    await message.delete()
                except Exception:
                    pass

                try:

                    warning = await message.channel.send(
                        f"⚠️ {message.author.mention} "
                        "**duplicate message detected.**"
                    )

                    await asyncio.sleep(2)

                    try:
                        await warning.delete()
                    except Exception:
                        pass

                except Exception:
                    pass

                return

            self.duplicate_cache[key] = content

            asyncio.create_task(
                self.clear_duplicate(
                    key,
                    content
                )
            )

        # ====================================================
        # ANTI-LINK
        # ====================================================

        if settings.get(
            "antilink",
            True
        ):

            link_patterns = (
                "http://",
                "https://",
                "www.",
                "discord.gg/",
                "discord.com/invite/"
            )

            is_link = any(
                x in lower_content
                for x in link_patterns
            )

            if is_link:

                # Server owner
                if message.author.id == message.guild.owner_id:
                    return

                # Bot owner
                if message.author.id in BOT_OWNER_IDS:
                    return

                # Owner role
                if self.has_owner_role(
                    message.author
                ):
                    return

                # Bot owner API
                try:

                    if await self.bot.is_owner(
                        message.author
                    ):
                        return

                except Exception:
                    pass

                # Music whitelist
                if self.is_music_command(content):

                    if self.music_whitelisted(
                        message.guild.id,
                        message.author.id
                    ):
                        return

                # Delete
                try:

                    await message.delete()

                except Exception as e:

                    print(
                        "[SECURITY] LINK DELETE ERROR:",
                        repr(e)
                    )

                # Timeout
                try:

                    await message.author.timeout(
                        timedelta(minutes=10),
                        reason="HSL Anti-Link"
                    )

                except Exception:
                    pass

                try:

                    warning = await message.channel.send(
                        f"🔗 {message.author.mention} "
                        "**link detected — 10 minute timeout.**"
                    )

                    await asyncio.sleep(2)

                    try:
                        await warning.delete()
                    except Exception:
                        pass

                except Exception:
                    pass

                return


    # ========================================================
    # DUPLICATE CACHE CLEANER
    # ========================================================

    async def clear_duplicate(
        self,
        key,
        content
    ):

        await asyncio.sleep(10)

        if self.duplicate_cache.get(key) == content:

            self.duplicate_cache.pop(
                key,
                None
            )


    # ========================================================
    # COMMAND ERROR
    # ========================================================

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx,
        error
    ):

        if isinstance(
            error,
            commands.CommandNotFound
        ):
            return

        if isinstance(
            error,
            commands.MissingRequiredArgument
        ):

            try:

                await ctx.send(
                    "❌ **Missing argument.**",
                    delete_after=5
                )

            except Exception:
                pass

            return

        if isinstance(
            error,
            commands.MemberNotFound
        ):

            try:

                await ctx.send(
                    "❌ **Member nahi mila.**",
                    delete_after=5
                )

            except Exception:
                pass

            return

        if isinstance(
            error,
            commands.RoleNotFound
        ):

            try:

                await ctx.send(
                    "❌ **Role nahi mila.**",
                    delete_after=5
                )

            except Exception:
                pass

            return

        if isinstance(
            error,
            commands.BadArgument
        ):

            try:

                await ctx.send(
                    "❌ **Invalid argument.**",
                    delete_after=5
                )

            except Exception:
                pass

            return

        print(
            "[SECURITY] COMMAND ERROR:",
            repr(error)
        )


    # ========================================================
    # READY
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(self):

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        print(
            "🛡️ HSL-CORP SECURITY ONLINE"
        )

        print(
            "👑 Server Owner: ALLOWED"
        )

        print(
            "🤖 Bot Owners: ALLOWED"
        )

        print(
            "🎭 Owner Roles: "
            f"{len(OWNER_ROLE_IDS)}"
        )

        print(
            "🤬 Anti-Gali: ENABLED"
        )

        print(
            "🤬 Gali Whitelist: ENABLED"
        )

        print(
            "🤖 Strict Anti-Bot: ENABLED"
        )

        print(
            "🔗 Anti-Link: ENABLED"
        )

        print(
            "♻️ Duplicate Protection: ENABLED"
        )

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Security(bot)
    )

    print(
        "🛡️ security.py successfully loaded"
    )