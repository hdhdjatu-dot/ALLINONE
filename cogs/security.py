import asyncio
import json
import os
from datetime import timedelta

import discord
from discord.ext import commands


# ============================================================
# HSL-CORP SECURITY
# ============================================================

DATA_FILE = "security_data.json"


# ============================================================
# BOT OWNERS
# ============================================================

# Discord USER IDs
BOT_OWNER_IDS = {
    1519933809402056805,
    1435943252455981080,
    1517901703263944758,
    1128339001548476426,
}


# ============================================================
# OWNER ROLE IDS
# ============================================================
#
# Anyone having one of these roles can use OWNER commands.
#
# You can add more role IDs here.
#
# Example:
#
# OWNER_ROLE_IDS = {
#     1451197118025826364,
#     123456789012345678,
# }
#

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
    "whitelist_music": [],
    "whitelist_bots": [],
}


# ============================================================
# DATA LOAD
# ============================================================

def load_data():

    if not os.path.exists(DATA_FILE):
        return {}

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, dict):
                return data

            return {}

    except Exception as e:

        print(
            "[SECURITY] DATA LOAD ERROR:",
            repr(e)
        )

        return {}


# ============================================================
# DATA SAVE
# ============================================================

def save_data(data):

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4
            )

    except Exception as e:

        print(
            "[SECURITY] DATA SAVE ERROR:",
            repr(e)
        )


# ============================================================
# SECURITY COG
# ============================================================

class Security(commands.Cog):

    def __init__(self, bot):

        self.bot = bot
        self.data = load_data()
        self.duplicate_cache = {}

        print(
            "🛡️ HSL-CORP Security loaded"
        )


    # ========================================================
    # GET SETTINGS
    # ========================================================

    def get_settings(
        self,
        guild_id
    ):

        guild_id = str(guild_id)

        if guild_id not in self.data:

            self.data[guild_id] = {}

            for key, value in DEFAULT_SETTINGS.items():

                if isinstance(value, list):

                    self.data[guild_id][key] = list(value)

                else:

                    self.data[guild_id][key] = value

            save_data(self.data)

        settings = self.data[guild_id]

        changed = False

        for key, value in DEFAULT_SETTINGS.items():

            if key not in settings:

                if isinstance(value, list):

                    settings[key] = list(value)

                else:

                    settings[key] = value

                changed = True

        # Normalize music whitelist

        if not isinstance(
            settings.get("whitelist_music"),
            list
        ):

            settings["whitelist_music"] = []
            changed = True

        cleaned_music = []

        for user_id in settings["whitelist_music"]:

            try:

                cleaned_music.append(
                    int(user_id)
                )

            except (
                TypeError,
                ValueError
            ):

                changed = True

        if cleaned_music != settings["whitelist_music"]:

            settings["whitelist_music"] = cleaned_music
            changed = True

        # Normalize bot whitelist

        if not isinstance(
            settings.get("whitelist_bots"),
            list
        ):

            settings["whitelist_bots"] = []
            changed = True

        cleaned_bots = []

        for bot_id in settings["whitelist_bots"]:

            try:

                cleaned_bots.append(
                    int(bot_id)
                )

            except (
                TypeError,
                ValueError
            ):

                changed = True

        cleaned_bots = list(
            dict.fromkeys(cleaned_bots)
        )

        if cleaned_bots != settings["whitelist_bots"]:

            settings["whitelist_bots"] = cleaned_bots
            changed = True

        if changed:
            save_data(self.data)

        return settings


    # ========================================================
    # BOT OWNER CHECK
    # ========================================================

    async def is_bot_owner(
        self,
        user
    ):

        if not user:
            return False

        if user.id in BOT_OWNER_IDS:
            return True

        try:

            if await self.bot.is_owner(user):
                return True

        except Exception as e:

            print(
                "[SECURITY] BOT OWNER CHECK ERROR:",
                repr(e)
            )

        return False


    # ========================================================
    # OWNER ROLE CHECK
    # ========================================================

    def has_owner_role(
        self,
        member
    ):

        if not isinstance(
            member,
            discord.Member
        ):

            return False

        for role in member.roles:

            if role.id in OWNER_ROLE_IDS:

                return True

        return False


    # ========================================================
    # MASTER OWNER CHECK
    # ========================================================
    #
    # Allowed:
    #
    # 1. Server owner
    # 2. Bot owner
    # 3. User having configured owner role
    #

    async def is_owner(
        self,
        member
    ):

        if not member:
            return False

        if not isinstance(
            member,
            discord.Member
        ):

            return False

        if not member.guild:
            return False

        # SERVER OWNER

        if member.id == member.guild.owner_id:
            return True

        # BOT OWNER

        if await self.is_bot_owner(member):
            return True

        # OWNER ROLE

        if self.has_owner_role(member):
            return True

        return False


    # ========================================================
    # OWNER ONLY ERROR
    # ========================================================

    async def owner_only_message(
        self,
        ctx
    ):

        try:

            await ctx.send(
                "❌ **Only the Server Owner, Bot Owner, "
                "or configured Owner Role can use this command.**",
                delete_after=5
            )

        except Exception:
            pass


    # ========================================================
    # STATUS
    # ========================================================

    def status(
        self,
        value
    ):

        return (
            "🟢 **ON**"
            if value
            else
            "🔴 **OFF**"
        )


    # ========================================================
    # SECURITY ANIMATION
    # ========================================================

    async def security_animation(
        self,
        ctx,
        enabled
    ):

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
            ("♻️", "DUPLICATE GUARD", "duplicate")

        ]

        settings = self.get_settings(
            ctx.guild.id
        )

        # INTRO

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

            await asyncio.sleep(
                0.16
            )

        completed = []

        for index, (
            emoji,
            name,
            key
        ) in enumerate(systems):

            for frame_index in range(7):

                frame = spinner[
                    frame_index % len(spinner)
                ]

                percent = int(
                    (
                        (
                            index
                            +
                            (
                                frame_index / 7
                            )
                        )
                        /
                        len(systems)
                    )
                    * 100
                )

                percent = min(
                    percent,
                    99
                )

                bar_length = 20

                filled = int(
                    (
                        percent / 100
                    )
                    * bar_length
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

                await message.edit(

                    content=(

                        "```ansi\n"

                        "\u001b[1;32m"
                        "╔══════════════════════════════╗\n"
                        "║       HSL-CORP SECURITY      ║\n"
                        "╠══════════════════════════════╣\n"

                        f"{old_lines}"

                        "║                              ║\n"

                        f"║   {frame} "
                        f"\u001b[1;37m"
                        f"{emoji} {name}"
                        "\u001b[1;32m      ║\n"

                        "║                              ║\n"

                        f"║   [{bar}] ║\n"

                        f"║             {percent:>3}%            ║\n"

                        "║                              ║\n"

                        "║   \u001b[1;33m◉ SCANNING SECURITY..."
                        "\u001b[1;32m ║\n"

                        "║                              ║\n"

                        "╚══════════════════════════════╝\n"

                        "\u001b[0m"
                        "```"
                    )
                )

                await asyncio.sleep(
                    0.13
                )

            settings[key] = enabled

            save_data(
                self.data
            )

            completed.append(
                (
                    emoji,
                    name
                )
            )

            old_lines = ""

            for old in completed:

                old_lines += (
                    f"║   {old[0]} "
                    f"{old[1]:<18} "
                    "✓ READY ║\n"
                )

            await message.edit(

                content=(

                    "```ansi\n"

                    "\u001b[1;32m"
                    "╔══════════════════════════════╗\n"
                    "║       HSL-CORP SECURITY      ║\n"
                    "╠══════════════════════════════╣\n"

                    f"{old_lines}"

                    "║                              ║\n"

                    f"║       {emoji} "
                    f"\u001b[1;37m{name}\u001b[1;32m       ║\n"

                    "║                              ║\n"

                    "║       ████████████████████   ║\n"
                    "║            100%              ║\n"

                    "║                              ║\n"

                    "║       \u001b[1;32m✓ PROTECTED"
                    "\u001b[1;32m         ║\n"

                    "║                              ║\n"

                    "╚══════════════════════════════╝\n"

                    "\u001b[0m"
                    "```"
                )
            )

            await asyncio.sleep(
                0.45
            )

        final_text = (
            "SYSTEM ONLINE"
            if enabled
            else
            "SYSTEM OFFLINE"
        )

        for i in range(8):

            frame = spinner[
                i % len(spinner)
            ]

            await message.edit(

                content=(

                    "```ansi\n"

                    "\u001b[1;32m"
                    "╔══════════════════════════════╗\n"
                    "║                              ║\n"
                    "║       H S L - C O R P        ║\n"
                    "║                              ║\n"

                    f"║       {frame} "
                    f"\u001b[1;37m"
                    f"{final_text}"
                    "\u001b[1;32m       ║\n"

                    "║                              ║\n"

                    "║       ✓ ANTI-LINK            ║\n"
                    "║       ✓ ANTI-BOT             ║\n"
                    "║       ✓ ANTI-NUKE            ║\n"
                    "║       ✓ ANTI-MOD             ║\n"
                    "║       ✓ ANTI-SPAM            ║\n"
                    "║       ✓ DUPLICATE GUARD      ║\n"

                    "║                              ║\n"

                    "║   ████████████████████████   ║\n"
                    "║          100% SECURE         ║\n"

                    "║                              ║\n"

                    "╚══════════════════════════════╝\n"

                    "\u001b[0m"
                    "```"
                )
            )

            await asyncio.sleep(
                0.18
            )

        await asyncio.sleep(5)

        try:
            await message.delete()
        except Exception:
            pass


    # ========================================================
    # ENABLE
    # ========================================================

    @commands.hybrid_command(
        name="antinukeenable",
        description="Enable HSL-CORP security"
    )
    @commands.guild_only()
    async def antinukeenable(
        self,
        ctx
    ):

        if not await self.is_owner(ctx.author):

            return await self.owner_only_message(ctx)

        await self.security_animation(
            ctx,
            True
        )


    # ========================================================
    # DISABLE
    # ========================================================

    @commands.hybrid_command(
        name="antinukedisable",
        description="Disable HSL-CORP security"
    )
    @commands.guild_only()
    async def antinukedisable(
        self,
        ctx
    ):

        if not await self.is_owner(ctx.author):

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
    async def automodstatus(
        self,
        ctx
    ):

        settings = self.get_settings(
            ctx.guild.id
        )

        embed = discord.Embed(

            title="🛡️ HSL-CORP SECURITY STATUS",

            description=(

                "```ansi\n"
                "\u001b[1;32m"

                "╔══════════════════════════╗\n"
                "║    SECURITY MONITOR      ║\n"
                "╠══════════════════════════╣\n"

                f"║ 🔗 Anti-Link      "
                f"{'🟢 ON' if settings['antilink'] else '🔴 OFF'} ║\n"

                f"║ 🤖 Anti-Bot       "
                f"{'🟢 ON' if settings['antibot'] else '🔴 OFF'} ║\n"

                f"║ ☢️ Anti-Nuke      "
                f"{'🟢 ON' if settings['antinuke'] else '🔴 OFF'} ║\n"

                f"║ 🔨 Anti-Mod       "
                f"{'🟢 ON' if settings['antimod'] else '🔴 OFF'} ║\n"

                f"║ 💬 Anti-Spam      "
                f"{'🟢 ON' if settings['antispam'] else '🔴 OFF'} ║\n"

                f"║ ♻️ Duplicate      "
                f"{'🟢 ON' if settings['duplicate'] else '🔴 OFF'} ║\n"

                "╚══════════════════════════╝\n"

                "\u001b[0m"
                "```"
            ),

            color=discord.Color.dark_green()
        )

        embed.set_footer(
            text="HSL-CORP • Security System"
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
    async def clear(
        self,
        ctx,
        amount: int
    ):

        if not await self.is_owner(ctx.author):

            return await self.owner_only_message(ctx)

        if amount < 1 or amount > 100:

            return await ctx.send(
                "❌ Amount `1-100` ke beech hona chahiye.",
                delete_after=4
            )

        try:

            # For slash command there is no source message.
            # For prefix command, delete the command too.

            limit = amount

            if ctx.message:
                limit += 1

            deleted = await ctx.channel.purge(
                limit=limit
            )

            count = len(deleted)

            if ctx.message and ctx.message in deleted:
                count -= 1

            count = max(
                0,
                count
            )

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
    async def say(
        self,
        ctx,
        *,
        text: str
    ):

        # HARD OWNER CHECK

        if not await self.is_owner(ctx.author):

            return await self.owner_only_message(ctx)

        if not text or not text.strip():

            return await ctx.send(
                "❌ **Message empty nahi ho sakta.**\n"
                "Use: `!say Hello`",
                delete_after=5
            )

        text = text.strip()

        try:

            # Send BOT message first.

            await ctx.send(
                text,
                allowed_mentions=discord.AllowedMentions.none()
            )

            # Delete only prefix command.
            #
            # Discord API slash commands do not create
            # a normal message, so this only applies to !say.

            if ctx.message:

                try:
                    await ctx.message.delete()
                except Exception:
                    pass

        except discord.Forbidden:

            try:

                await ctx.send(
                    "❌ **Mujhe message send karne ki permission nahi hai.**",
                    delete_after=5
                )

            except Exception:
                pass

        except discord.HTTPException as e:

            print(
                "[SECURITY] SAY HTTP ERROR:",
                repr(e)
            )

        except Exception as e:

            print(
                "[SECURITY] SAY ERROR:",
                repr(e)
            )


    # ========================================================
    # WHITELIST BOT
    # ========================================================
    #
    # Usage:
    #
    # !whitelistbot @Bot
    #
    # !whitelistbot @Bot remove
    #
    # /whitelistbot bot:@Bot
    #
    # ONLY:
    #
    # Server Owner
    # Bot Owner
    # Owner Role
    #

    @commands.hybrid_command(
        name="whitelistbot",
        description="Whitelist or remove a bot from Anti-Bot"
    )
    @commands.guild_only()
    async def whitelistbot(
        self,
        ctx,
        member: discord.Member,
        action: str = "add"
    ):

        if not await self.is_owner(ctx.author):

            return await self.owner_only_message(ctx)

        if not member.bot:

            return await ctx.send(
                "❌ Ye member bot nahi hai.",
                delete_after=5
            )

        action = str(
            action
        ).lower().strip()

        settings = self.get_settings(
            ctx.guild.id
        )

        bots = settings.setdefault(
            "whitelist_bots",
            []
        )

        # Normalize

        normalized = []

        for bot_id in bots:

            try:

                normalized.append(
                    int(bot_id)
                )

            except (
                TypeError,
                ValueError
            ):
                pass

        bots = list(
            dict.fromkeys(normalized)
        )

        settings["whitelist_bots"] = bots

        # ====================================================
        # ADD
        # ====================================================

        if action in (
            "add",
            "on",
            "enable",
            "toggle"
        ):

            if member.id in bots:

                return await ctx.send(
                    f"🟢 {member.mention} "
                    "**already whitelist mein hai.**",
                    delete_after=5
                )

            bots.append(
                member.id
            )

            settings["whitelist_bots"] = bots

            save_data(
                self.data
            )

            return await ctx.send(
                f"🤖 {member.mention} "
                "**successfully bot whitelist mein add ho gaya.**\n"
                "✅ Ab Anti-Bot is bot ko allow karega.",
                delete_after=7
            )


        # ====================================================
        # REMOVE
        # ====================================================

        if action in (
            "remove",
            "delete",
            "del",
            "off",
            "disable"
        ):

            if member.id not in bots:

                return await ctx.send(
                    f"🟡 {member.mention} "
                    "**bot whitelist mein nahi hai.**",
                    delete_after=5
                )

            bots.remove(
                member.id
            )

            settings["whitelist_bots"] = bots

            save_data(
                self.data
            )

            return await ctx.send(
                f"🔴 {member.mention} "
                "**bot whitelist se remove ho gaya.**",
                delete_after=6
            )


        # ====================================================
        # INVALID
        # ====================================================

        return await ctx.send(
            "❌ Invalid action.\n\n"
            "**Use:**\n"
            "`!whitelistbot @Bot`\n"
            "`!whitelistbot @Bot remove`",
            delete_after=7
        )


    # ========================================================
    # LIST WHITELISTED BOTS
    # ========================================================

    @commands.hybrid_command(
        name="whitelistbots",
        description="Show whitelisted bots"
    )
    @commands.guild_only()
    async def whitelistbots(
        self,
        ctx
    ):

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
            start=1
        ):

            bot_member = ctx.guild.get_member(
                int(bot_id)
            )

            if bot_member:

                lines.append(
                    f"**{index}.** "
                    f"{bot_member.mention} "
                    f"`{bot_member.id}`"
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

        embed.set_footer(
            text="Only Server Owner / Bot Owner / Owner Role can manage this."
        )

        await ctx.send(
            embed=embed
        )


    # ========================================================
    # MUSIC WHITELIST
    # ========================================================

    @commands.hybrid_command(
        name="whitelist",
        description="Manage music link whitelist"
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

        normalized_users = []

        for user_id in users:

            try:

                normalized_users.append(
                    int(user_id)
                )

            except (
                TypeError,
                ValueError
            ):

                pass

        settings["whitelist_music"] = list(
            dict.fromkeys(
                normalized_users
            )
        )

        users = settings["whitelist_music"]

        # SHOW LIST

        if member is None:

            if not users:

                embed = discord.Embed(
                    title="🎵 HSL-CORP MUSIC WHITELIST",
                    description=(
                        "No members are currently "
                        "music-whitelisted."
                    ),
                    color=discord.Color.orange()
                )

                return await ctx.send(
                    embed=embed
                )

            lines = []

            for index, user_id in enumerate(
                users,
                start=1
            ):

                guild_member = ctx.guild.get_member(
                    user_id
                )

                if guild_member:

                    lines.append(
                        f"**{index}.** "
                        f"{guild_member.mention} "
                        f"`{guild_member.id}`"
                    )

                else:

                    lines.append(
                        f"**{index}.** "
                        f"<@{user_id}> "
                        f"`{user_id}`"
                    )

            embed = discord.Embed(
                title="🎵 HSL-CORP MUSIC WHITELIST",
                description="\n".join(lines),
                color=discord.Color.green()
            )

            embed.add_field(
                name="Allowed Commands",
                value="`!play` • `!p` • `/play` • `/p`",
                inline=False
            )

            return await ctx.send(
                embed=embed
            )

        action = str(
            action
        ).lower().strip()

        if action not in (
            "add",
            "remove",
            "delete",
            "del",
            "off",
            "disable",
            "on",
            "enable",
            "toggle"
        ):

            return await ctx.send(
                "❌ Invalid action.\n\n"
                "`/whitelist @User`\n"
                "`/whitelist @User add`\n"
                "`/whitelist @User remove`",
                delete_after=8
            )

        # REMOVE

        if action in (
            "remove",
            "delete",
            "del",
            "off",
            "disable"
        ):

            if member.id not in users:

                return await ctx.send(
                    f"🟡 {member.mention} "
                    "**music whitelist mein nahi hai.**",
                    delete_after=5
                )

            users.remove(
                member.id
            )

            save_data(
                self.data
            )

            return await ctx.send(
                f"🔴 {member.mention} "
                "**music whitelist se remove ho gaya.**",
                delete_after=6
            )

        # ADD

        if action in (
            "add",
            "on",
            "enable"
        ):

            if member.id in users:

                return await ctx.send(
                    f"🟢 {member.mention} "
                    "**already music whitelist mein hai.**",
                    delete_after=5
                )

            users.append(
                member.id
            )

            save_data(
                self.data
            )

            return await ctx.send(
                f"🟢 {member.mention} "
                "**music whitelist mein add ho gaya.**",
                delete_after=8
            )

        # TOGGLE

        if member.id in users:

            users.remove(
                member.id
            )

            save_data(
                self.data
            )

            return await ctx.send(
                f"🟡 {member.mention} "
                "**music whitelist se remove ho gaya.**",
                delete_after=6
            )

        users.append(
            member.id
        )

        save_data(
            self.data
        )

        await ctx.send(
            f"🟢 {member.mention} "
            "**music whitelist mein add ho gaya.**",
            delete_after=8
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

        # OWNER CHECK

        if not await self.is_owner(ctx.author):

            return await self.owner_only_message(ctx)

        if role.is_default():

            return await ctx.send(
                "❌ `@everyone` role assign nahi kar sakte.",
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
                "❌ Bot member information unavailable.",
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
                reason=(
                    f"HSL Security giverole by "
                    f"{ctx.author}"
                )
            )

            await ctx.send(
                f"✅ {role.mention} "
                f"**{member.mention} ko de diya.**",
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
    #
    # Usage:
    #
    # !removerole @User @Role
    #

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

        # OWNER CHECK

        if not await self.is_owner(ctx.author):

            return await self.owner_only_message(ctx)

        if role.is_default():

            return await ctx.send(
                "❌ `@everyone` role remove nahi kar sakte.",
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
                "❌ Bot member information unavailable.",
                delete_after=5
            )

        if role >= me.top_role:

            return await ctx.send(
                "❌ Ye role bot ke highest role se upar hai.",
                delete_after=5
            )

        if role not in member.roles:

            return await ctx.send(
                f"🟡 {member.mention} ke paas "
                f"{role.mention} role hai hi nahi.",
                delete_after=5
            )

        try:

            await member.remove_roles(
                role,
                reason=(
                    f"HSL Security removerole by "
                    f"{ctx.author}"
                )
            )

            await ctx.send(
                f"✅ {role.mention} "
                f"**{member.mention} se remove kar diya.**",
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
    async def on_member_join(
        self,
        member: discord.Member
    ):

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

            print(
                f"[SECURITY] Anti-Bot disabled "
                f"in {guild.name}"
            )

            return

        # ====================================================
        # CHECK WHITELIST FIRST
        # ====================================================

        whitelist = settings.get(
            "whitelist_bots",
            []
        )

        try:

            if member.id in [
                int(x)
                for x in whitelist
            ]:

                print(
                    f"[SECURITY] ✅ WHITELISTED BOT ALLOWED: "
                    f"{member} ({member.id})"
                )

                return

        except Exception:
            pass

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        print(
            "🚨 HSL-CORP ANTI-BOT DETECTED"
        )

        print(
            f"🤖 Bot: {member} "
            f"({member.id})"
        )

        inviter = None

        # ====================================================
        # AUDIT LOG SEARCH
        # ====================================================

        for attempt in range(12):

            try:

                await asyncio.sleep(
                    0.75
                )

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
                        -
                        entry.created_at
                    ).total_seconds()

                    if age < 0:
                        continue

                    if age > 30:
                        continue

                    inviter = entry.user

                    print(
                        f"[SECURITY] 👤 Bot added by: "
                        f"{inviter} "
                        f"({inviter.id})"
                    )

                    break

                if inviter:
                    break

            except discord.Forbidden:

                print(
                    "[SECURITY] ❌ Cannot read audit logs."
                )

                print(
                    "[SECURITY] Give HSL-CORP "
                    "`View Audit Log` permission."
                )

                break

            except discord.HTTPException as e:

                print(
                    "[SECURITY] Audit HTTP error:",
                    repr(e)
                )

            except Exception as e:

                print(
                    "[SECURITY] Audit log error:",
                    repr(e)
                )

        # ====================================================
        # INVITER UNKNOWN
        # ====================================================

        if inviter is None:

            print(
                "[SECURITY] ⚠️ Inviter not found."
            )

            print(
                "[SECURITY] STRICT MODE → "
                "KICKING UNKNOWN BOT"
            )

            await self.kick_unauthorized_bot(
                member
            )

            print(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

            return

        # ====================================================
        # SERVER OWNER CAN ADD NON-WHITELISTED BOT
        # ====================================================

        if inviter.id == guild.owner_id:

            print(
                f"[SECURITY] 👑 SERVER OWNER "
                f"{inviter} added bot."
            )

            print(
                "[SECURITY] ✅ BOT ALLOWED"
            )

            print(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

            return

        # ====================================================
        # BOT OWNER DOES NOT GET BOT-ADD BYPASS
        # ====================================================
        #
        # IMPORTANT:
        #
        # You specifically wanted strict Anti-Bot where
        # only SERVER OWNER can add a normal non-whitelisted bot.
        #
        # Therefore BOT OWNER / OWNER ROLE cannot bypass
        # this anti-bot rule.
        #
        # They can use !whitelistbot first.
        #

        print(
            "🚨🚨🚨 UNAUTHORIZED BOT ADDITION 🚨🚨🚨"
        )

        print(
            f"[SECURITY] 🤖 Bot: "
            f"{member} ({member.id})"
        )

        print(
            f"[SECURITY] 👤 Inviter: "
            f"{inviter} ({inviter.id})"
        )

        inviter_member = None

        if isinstance(
            inviter,
            discord.Member
        ):

            inviter_member = inviter

        else:

            try:

                inviter_member = guild.get_member(
                    inviter.id
                )

                if inviter_member is None:

                    inviter_member = (
                        await guild.fetch_member(
                            inviter.id
                        )
                    )

            except discord.NotFound:

                print(
                    "[SECURITY] Inviter no longer "
                    "in server."
                )

            except Exception as e:

                print(
                    "[SECURITY] Inviter fetch error:",
                    repr(e)
                )

        # KICK BOT

        await self.kick_unauthorized_bot(
            member
        )

        # REMOVE INVITER ROLES

        if inviter_member:

            await self.remove_inviter_roles(
                inviter_member
            )

        print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )


    # ========================================================
    # KICK UNAUTHORIZED BOT
    # ========================================================

    async def kick_unauthorized_bot(
        self,
        member: discord.Member
    ):

        guild = member.guild

        me = guild.me

        if me is None:

            print(
                "[SECURITY] ❌ HSL-CORP member "
                "not available."
            )

            return False

        if not me.guild_permissions.kick_members:

            print(
                "[SECURITY] ❌ KICK FAILED"
            )

            print(
                "[SECURITY] HSL-CORP does not have "
                "`Kick Members` permission."
            )

            return False

        if self.bot.user and member.id == self.bot.user.id:

            print(
                "[SECURITY] ❌ Target is HSL-CORP itself."
            )

            return False

        if member.top_role >= me.top_role:

            print(
                "[SECURITY] ❌ KICK BLOCKED BY "
                "ROLE HIERARCHY."
            )

            print(
                "[SECURITY] Move HSL-CORP's role "
                "ABOVE the unauthorized bot."
            )

            return False

        try:

            await member.kick(
                reason=(
                    "HSL-CORP Security - "
                    "Unauthorized bot addition"
                )
            )

            print(
                f"[SECURITY] ✅ BOT KICKED: "
                f"{member}"
            )

            return True

        except discord.Forbidden:

            print(
                "[SECURITY] ❌ Discord Forbidden "
                "while kicking bot."
            )

        except discord.HTTPException as e:

            print(
                "[SECURITY] ❌ Kick HTTP error:",
                repr(e)
            )

        except Exception as e:

            print(
                "[SECURITY] ❌ Kick error:",
                repr(e)
            )

        return False


    # ========================================================
    # REMOVE INVITER ROLES
    # ========================================================

    async def remove_inviter_roles(
        self,
        member: discord.Member
    ):

        if not member:
            return

        guild = member.guild

        # NEVER remove server owner's roles

        if member.id == guild.owner_id:

            print(
                "[SECURITY] Server owner → "
                "roles protected."
            )

            return

        me = guild.me

        if me is None:
            return

        if not me.guild_permissions.manage_roles:

            print(
                "[SECURITY] ❌ ROLE REMOVE FAILED"
            )

            print(
                "[SECURITY] HSL-CORP does not have "
                "`Manage Roles` permission."
            )

            return

        removable_roles = []

        for role in member.roles:

            if role.is_default():
                continue

            if role.managed:
                continue

            if role >= me.top_role:

                print(
                    f"[SECURITY] ⚠️ Cannot remove "
                    f"'{role.name}' — role is "
                    f"equal/higher than HSL."
                )

                continue

            removable_roles.append(
                role
            )

        if not removable_roles:

            print(
                "[SECURITY] ⚠️ No removable roles."
            )

            return

        removed = 0

        for role in removable_roles:

            try:

                await member.remove_roles(
                    role,
                    reason=(
                        "HSL-CORP Security - "
                        "Unauthorized bot addition"
                    )
                )

                removed += 1

                print(
                    f"[SECURITY] 🗑️ Removed role: "
                    f"{role.name}"
                )

                await asyncio.sleep(
                    0.2
                )

            except discord.Forbidden:

                print(
                    f"[SECURITY] ❌ FORBIDDEN removing "
                    f"role: {role.name}"
                )

            except discord.HTTPException as e:

                print(
                    f"[SECURITY] ❌ HTTP error removing "
                    f"{role.name}:",
                    repr(e)
                )

            except Exception as e:

                print(
                    f"[SECURITY] ❌ Role error "
                    f"{role.name}:",
                    repr(e)
                )

        print(
            f"[SECURITY] ✅ Removed "
            f"{removed}/{len(removable_roles)} "
            f"roles from {member}"
        )


    # ========================================================
    # MUSIC WHITELIST CHECK
    # ========================================================

    def music_whitelisted(
        self,
        guild_id,
        user_id
    ):

        settings = self.get_settings(
            guild_id
        )

        whitelist = settings.get(
            "whitelist_music",
            []
        )

        try:

            user_id = int(
                user_id
            )

        except (
            TypeError,
            ValueError
        ):

            return False

        for allowed_id in whitelist:

            try:

                if int(allowed_id) == user_id:
                    return True

            except (
                TypeError,
                ValueError
            ):

                continue

        return False


    # ========================================================
    # MUSIC COMMAND DETECTION
    # ========================================================

    def is_music_command(
        self,
        content
    ):

        if not content:
            return False

        content = content.strip().lower()

        if not content:
            return False

        first_word = content.split(
            maxsplit=1
        )[0]

        return first_word in (
            "!play",
            "!p",
            "/play",
            "/p"
        )


    # ========================================================
    # MESSAGE SECURITY
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        # Ignore bots

        if message.author.bot:
            return

        # Ignore DMs

        if not message.guild:
            return

        settings = self.get_settings(
            message.guild.id
        )

        content = (
            message.content
            or ""
        ).strip()

        lower_content = content.lower()

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

            if old == message.content:

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

                    await warning.delete()

                except Exception:
                    pass

                return

            self.duplicate_cache[key] = (
                message.content
            )

            asyncio.create_task(
                self.clear_duplicate(
                    key,
                    message.content
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
                pattern in lower_content
                for pattern in link_patterns
            )

            if is_link:

                # Server owner bypass

                if message.author.id == message.guild.owner_id:

                    return

                # Bot owner bypass

                if message.author.id in BOT_OWNER_IDS:

                    return

                # Owner role bypass

                if self.has_owner_role(
                    message.author
                ):

                    return

                # Discord.py owner

                try:

                    if await self.bot.is_owner(
                        message.author
                    ):

                        return

                except Exception:
                    pass

                # Music command

                is_music = self.is_music_command(
                    content
                )

                # Music whitelist

                if is_music:

                    allowed = self.music_whitelisted(
                        message.guild.id,
                        message.author.id
                    )

                    if allowed:

                        return

                # Delete link

                try:

                    await message.delete()

                except discord.Forbidden:

                    print(
                        "[SECURITY] ❌ Cannot delete link."
                    )

                except Exception as e:

                    print(
                        "[SECURITY] Delete error:",
                        repr(e)
                    )

                # Timeout

                try:

                    await message.author.timeout(

                        timedelta(
                            minutes=10
                        ),

                        reason=(
                            "HSL Anti-Link - "
                            "Unauthorized link"
                        )
                    )

                except discord.Forbidden:

                    print(
                        "[SECURITY] ❌ Cannot timeout user."
                    )

                except Exception as e:

                    print(
                        "[SECURITY] TIMEOUT ERROR:",
                        repr(e)
                    )

                # Warning

                try:

                    warning = await message.channel.send(

                        f"🔗 {message.author.mention} "
                        "**link detected — 10 minute timeout.**"
                    )

                    await asyncio.sleep(2)

                    await warning.delete()

                except Exception:
                    pass

                return


    # ========================================================
    # CLEAR DUPLICATE CACHE
    # ========================================================

    async def clear_duplicate(
        self,
        key,
        content
    ):

        await asyncio.sleep(
            10
        )

        if self.duplicate_cache.get(
            key
        ) == content:

            self.duplicate_cache.pop(
                key,
                None
            )


    # ========================================================
    # COMMAND ERROR HANDLER
    # ========================================================

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx,
        error
    ):

        # Ignore errors already handled elsewhere

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
                    "❌ **Missing argument.** "
                    "Command ko sahi format mein use karo.",
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

        print(
            "[SECURITY] COMMAND ERROR:",
            repr(error)
        )


    # ========================================================
    # READY
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(
        self
    ):

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
            f"🎭 Owner Roles: "
            f"{len(OWNER_ROLE_IDS)}"
        )

        print(
            "🤖 Strict Anti-Bot: ENABLED"
        )

        print(
            "🔗 Anti-Link"
        )

        print(
            "☢️ Anti-Nuke"
        )

        print(
            "🔨 Anti-Mod"
        )

        print(
            "💬 Anti-Spam"
        )

        print(
            "♻️ Duplicate Protection"
        )

        print(
            "🧹 Clear"
        )

        print(
            "🎵 Music Whitelist"
        )

        print(
            "🤖 Bot Whitelist"
        )

        print(
            "📢 Say Command"
        )

        print(
            "🎭 Give Role"
        )

        print(
            "🎭 Remove Role"
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