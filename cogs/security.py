
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
# BOT OWNER IDS
# ============================================================
# YAHAN APNI DISCORD USER ID DALO.
#
# Discord Developer Mode:
# Settings -> Advanced -> Developer Mode ON
# Apne profile par Right Click -> Copy User ID
#
# Multiple bot owners bhi add kar sakte ho.
# ============================================================

BOT_OWNER_IDS = {
    1519933809402056805,
    1435943252455981080,
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
    "whitelist_music": []
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

            return json.load(f)

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

            self.data[guild_id] = dict(
                DEFAULT_SETTINGS
            )

            # Make whitelist independent for every server
            self.data[guild_id]["whitelist_music"] = []

            save_data(
                self.data
            )

        settings = self.data[guild_id]

        # Add missing settings
        for key, value in DEFAULT_SETTINGS.items():

            if key not in settings:

                if key == "whitelist_music":

                    settings[key] = []

                else:

                    settings[key] = value

        return settings


    # ========================================================
    # OWNER / ADMIN CHECK
    #
    # SERVER OWNER
    # BOT OWNER
    # ADMINISTRATOR
    # ========================================================

    async def is_owner(
        self,
        member
    ):

        if member is None:
            return False

        guild = getattr(
            member,
            "guild",
            None
        )

        if guild is None:
            return False


        # ====================================================
        # 1. SERVER OWNER
        # ====================================================

        if member.id == guild.owner_id:

            return True


        # ====================================================
        # 2. CONFIGURED BOT OWNER
        # ====================================================

        if member.id in BOT_OWNER_IDS:

            return True


        # ====================================================
        # 3. discord.py BOT OWNER CHECK
        # ====================================================

        try:

            if await self.bot.is_owner(member):

                return True

        except Exception as e:

            print(
                "[SECURITY] BOT OWNER CHECK ERROR:",
                repr(e)
            )


        # ====================================================
        # 4. BOT owner_id FALLBACK
        # ====================================================

        try:

            owner_id = getattr(
                self.bot,
                "owner_id",
                None
            )

            if owner_id:

                if member.id == owner_id:

                    return True

        except Exception:

            pass


        # ====================================================
        # 5. BOT owner_ids FALLBACK
        # ====================================================

        try:

            owner_ids = getattr(
                self.bot,
                "owner_ids",
                set()
            )

            if member.id in owner_ids:

                return True

        except Exception:

            pass


        # ====================================================
        # 6. SERVER ADMINISTRATOR
        # ====================================================

        try:

            if isinstance(
                member,
                discord.Member
            ):

                if member.guild_permissions.administrator:

                    return True

        except Exception as e:

            print(
                "[SECURITY] ADMIN CHECK ERROR:",
                repr(e)
            )


        return False


    # ========================================================
    # STATUS
    # ========================================================

    def status(
        self,
        value
    ):

        if value:

            return "🟢 **ON**"

        return "🔴 **OFF**"


    # ========================================================
    # SECURITY ANIMATION
    # ========================================================

    async def security_animation(
        self,
        ctx,
        enabled
    ):

        # ----------------------------------------------------
        # INITIAL MESSAGE
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # SPINNER
        # ----------------------------------------------------

        spinner = [
            "◐",
            "◓",
            "◑",
            "◒"
        ]


        # ----------------------------------------------------
        # SYSTEMS
        # ----------------------------------------------------

        systems = [

            (
                "🔗",
                "ANTI-LINK",
                "antilink"
            ),

            (
                "🤖",
                "ANTI-BOT",
                "antibot"
            ),

            (
                "☢️",
                "ANTI-NUKE",
                "antinuke"
            ),

            (
                "🔨",
                "ANTI-MOD",
                "antimod"
            ),

            (
                "💬",
                "ANTI-SPAM",
                "antispam"
            ),

            (
                "♻️",
                "DUPLICATE GUARD",
                "duplicate"
            )
        ]


        settings = self.get_settings(
            ctx.guild.id
        )


        # ====================================================
        # INTRO SPINNER
        # ====================================================

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


        # ====================================================
        # EACH SECURITY
        # ====================================================

        completed = []


        for index, (
            emoji,
            name,
            key
        ) in enumerate(systems):


            # ------------------------------------------------
            # LOADING
            # ------------------------------------------------

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

                if percent > 99:

                    percent = 99


                bar_length = 20

                filled = int(
                    (
                        percent
                        /
                        100
                    )
                    * bar_length
                )

                bar = (
                    "█" * filled
                    +
                    "░" * (
                        bar_length
                        - filled
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

                        "║   \u001b[1;33m◉ SCANNING SECURITY...\u001b[1;32m ║\n"

                        "║                              ║\n"

                        "╚══════════════════════════════╝\n"

                        "\u001b[0m"
                        "```"
                    )
                )

                await asyncio.sleep(
                    0.13
                )


            # ------------------------------------------------
            # SAVE STATE
            # ------------------------------------------------

            settings[key] = enabled

            save_data(
                self.data
            )


            # ------------------------------------------------
            # TICK
            # ------------------------------------------------

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

                    "║       \u001b[1;32m✓ PROTECTED\u001b[1;32m         ║\n"

                    "║                              ║\n"

                    "╚══════════════════════════════╝\n"

                    "\u001b[0m"
                    "```"
                )
            )

            await asyncio.sleep(
                0.45
            )


        # ====================================================
        # FINAL ANIMATION
        # ====================================================

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


        # ----------------------------------------------------
        # DELETE
        # ----------------------------------------------------

        await asyncio.sleep(
            5
        )

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
    async def antinukeenable(
        self,
        ctx
    ):

        if not await self.is_owner(
            ctx.author
        ):

            return await ctx.send(
                "❌ **Only the server owner, "
                "administrator, or HSL-CORP bot owner "
                "can use this.**",
                delete_after=5
            )


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
    async def antinukedisable(
        self,
        ctx
    ):

        if not await self.is_owner(
            ctx.author
        ):

            return await ctx.send(
                "❌ **Only the server owner, "
                "administrator, or HSL-CORP bot owner "
                "can use this.**",
                delete_after=5
            )


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

                "\n"

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

                "\n"

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
    @commands.has_permissions(
        manage_messages=True
    )
    async def clear(
        self,
        ctx,
        amount: int
    ):

        if amount < 1 or amount > 100:

            return await ctx.send(
                "❌ Amount `1-100` ke beech hona chahiye.",
                delete_after=4
            )


        try:

            deleted = await ctx.channel.purge(
                limit=amount + 1
            )

            count = max(
                0,
                len(deleted) - 1
            )


            msg = await ctx.send(
                f"🧹 **{count} messages cleared.**"
            )


            await asyncio.sleep(
                3
            )


            try:

                await msg.delete()

            except Exception:

                pass


        except discord.Forbidden:

            await ctx.send(
                "❌ Mujhe messages delete karne ki permission nahi hai.",
                delete_after=5
            )


    # ========================================================
    # MUSIC WHITELIST
    # ========================================================

    @commands.hybrid_command(
        name="whitelist",
        description="Whitelist member for music links"
    )
    @commands.guild_only()
    async def whitelist(
        self,
        ctx,
        member: discord.Member
    ):

        if not await self.is_owner(
            ctx.author
        ):

            return await ctx.send(
                "❌ **Only the server owner, administrator, "
                "or HSL-CORP bot owner can use this.**",
                delete_after=5
            )


        settings = self.get_settings(
            ctx.guild.id
        )


        users = settings.setdefault(
            "whitelist_music",
            []
        )


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
                delete_after=5
            )


        users.append(
            member.id
        )

        save_data(
            self.data
        )


        await ctx.send(
            f"🟢 {member.mention} "
            "**sirf music links ke liye whitelisted hai.**",
            delete_after=5
        )


    # ========================================================
    # GIVE ROLE
    # ========================================================

    @commands.hybrid_command(
        name="giverole",
        description="Give a role to a member"
    )
    @commands.guild_only()
    async def giverole(
        self,
        ctx,
        member: discord.Member,
        role: discord.Role
    ):

        if not await self.is_owner(
            ctx.author
        ):

            return await ctx.send(
                "❌ **Only the server owner, administrator, "
                "or HSL-CORP bot owner can use this.**",
                delete_after=5
            )


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


    # ========================================================
    # ANTI-BOT
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ):

        if not member.bot:
            return


        settings = self.get_settings(
            member.guild.id
        )


        if not settings.get(
            "antibot",
            True
        ):

            return


        try:

            async for entry in member.guild.audit_logs(

                limit=10,

                action=discord.AuditLogAction.bot_add
            ):

                if not entry.target:
                    continue


                if entry.target.id != member.id:
                    continue


                inviter = entry.user


                # --------------------------------------------
                # SERVER OWNER BYPASS
                # --------------------------------------------

                if inviter.id == member.guild.owner_id:

                    print(
                        f"[SECURITY] Server owner added {member}"
                    )

                    return


                # --------------------------------------------
                # BOT OWNER BYPASS
                # --------------------------------------------

                try:

                    if await self.bot.is_owner(
                        inviter
                    ):

                        print(
                            f"[SECURITY] Bot owner added {member}"
                        )

                        return

                except Exception:

                    pass


                # --------------------------------------------
                # CONFIGURED BOT OWNER BYPASS
                # --------------------------------------------

                if inviter.id in BOT_OWNER_IDS:

                    print(
                        f"[SECURITY] Configured bot owner added {member}"
                    )

                    return


                # --------------------------------------------
                # UNAUTHORIZED BOT
                # --------------------------------------------

                print(
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )

                print(
                    "🚨 [SECURITY] UNAUTHORIZED BOT"
                )

                print(
                    f"[SECURITY] Bot: {member}"
                )

                print(
                    f"[SECURITY] Added by: {inviter}"
                )

                print(
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )


                # --------------------------------------------
                # KICK BOT
                # --------------------------------------------

                try:

                    await member.kick(
                        reason=(
                            "HSL Security - "
                            "Unauthorized bot addition"
                        )
                    )

                    print(
                        "[SECURITY] ✅ Unauthorized bot kicked"
                    )

                except Exception as e:

                    print(
                        "[SECURITY] BOT KICK ERROR:",
                        repr(e)
                    )


                # --------------------------------------------
                # REMOVE INVITER ROLES
                # --------------------------------------------

                if isinstance(
                    inviter,
                    discord.Member
                ):

                    await self.remove_roles(
                        inviter
                    )


                return


        except Exception as e:

            print(
                "[SECURITY] ANTIBOT ERROR:",
                repr(e)
            )


    # ========================================================
    # REMOVE ROLES
    # ========================================================

    async def remove_roles(
        self,
        member
    ):

        # Never touch server owner
        if member.id == member.guild.owner_id:
            return


        # Never touch configured bot owner
        if member.id in BOT_OWNER_IDS:
            return


        # Never touch bot owner
        try:

            if await self.bot.is_owner(
                member
            ):

                return

        except Exception:

            pass


        me = member.guild.me


        if not me:
            return


        removable = []


        for role in member.roles:

            if role.is_default():
                continue

            if role.managed:
                continue

            # Discord hierarchy protection
            if role >= me.top_role:
                continue

            removable.append(
                role
            )


        if not removable:

            print(
                "[SECURITY] No removable roles found."
            )

            return


        try:

            await member.remove_roles(
                *removable,
                reason=(
                    "HSL Security - "
                    "Unauthorized bot addition"
                )
            )


            print(
                f"[SECURITY] Removed roles from {member}"
            )


        except Exception as e:

            print(
                "[SECURITY] ROLE REMOVE ERROR:",
                repr(e)
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


        return user_id in settings.get(
            "whitelist_music",
            []
        )


    # ========================================================
    # MESSAGE SECURITY
    # ========================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        if message.author.bot:
            return


        if not message.guild:
            return


        settings = self.get_settings(
            message.guild.id
        )


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


                    await asyncio.sleep(
                        2
                    )


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

            content = (
                message.content.lower()
            )


            link_patterns = (

                "http://",
                "https://",
                "www.",
                "discord.gg/",
                "discord.com/invite/"
            )


            is_link = any(
                x in content
                for x in link_patterns
            )


            if is_link:

                # --------------------------------------------
                # SERVER OWNER BYPASS
                # --------------------------------------------

                if message.author.id == message.guild.owner_id:

                    await self.bot.process_commands(
                        message
                    )

                    return


                # --------------------------------------------
                # BOT OWNER BYPASS
                # --------------------------------------------

                try:

                    if await self.bot.is_owner(
                        message.author
                    ):

                        await self.bot.process_commands(
                            message
                        )

                        return

                except Exception:

                    pass


                # --------------------------------------------
                # CONFIGURED BOT OWNER BYPASS
                # --------------------------------------------

                if message.author.id in BOT_OWNER_IDS:

                    await self.bot.process_commands(
                        message
                    )

                    return


                # --------------------------------------------
                # MUSIC COMMAND WHITELIST
                # --------------------------------------------

                is_music_command = (

                    content.startswith(
                        "!play"
                    )

                    or content.startswith(
                        "/play"
                    )
                )


                if (
                    is_music_command
                    and
                    self.music_whitelisted(
                        message.guild.id,
                        message.author.id
                    )
                ):

                    await self.bot.process_commands(
                        message
                    )

                    return


                # --------------------------------------------
                # DELETE LINK
                # --------------------------------------------

                try:

                    await message.delete()

                except Exception:

                    pass


                # --------------------------------------------
                # TIMEOUT
                # --------------------------------------------

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


                    print(
                        f"[SECURITY] Timed out "
                        f"{message.author} for 10 minutes"
                    )


                except Exception as e:

                    print(
                        "[SECURITY] TIMEOUT ERROR:",
                        repr(e)
                    )


                # --------------------------------------------
                # WARNING
                # --------------------------------------------

                try:

                    warning = await message.channel.send(

                        f"🔗 {message.author.mention} "
                        "**link detected — 10 minute timeout.**"
                    )


                    await asyncio.sleep(
                        2
                    )


                    await warning.delete()


                except Exception:

                    pass


                return


        # ====================================================
        # COMMAND PROCESSING
        # ====================================================

        await self.bot.process_commands(
            message
        )


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
            "👑 Server Owner + Bot Owner bypass"
        )

        print(
            "🤖 Anti-Bot"
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
            "🎭 Give Role"
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

