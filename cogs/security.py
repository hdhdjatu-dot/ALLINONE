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
# IMPORTANT:
# Yahan DISCORD USER IDs hone chahiye.
# Server IDs nahi.
# Server OWNER ko automatically bypass milega.

BOT_OWNER_IDS = {
    1519933809402056805,
    1435943252455981080,
    1517901703263944758,
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

    def get_settings(self, guild_id):

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

        # Add missing settings automatically
        for key, value in DEFAULT_SETTINGS.items():

            if key not in settings:

                if isinstance(value, list):

                    settings[key] = list(value)

                else:

                    settings[key] = value

        # Make sure whitelist is valid
        if not isinstance(
            settings.get("whitelist_music"),
            list
        ):

            settings["whitelist_music"] = []

        return settings


    # ========================================================
    # SERVER OWNER / BOT OWNER CHECK
    # ========================================================

    async def is_owner(self, member):

        if not member:
            return False

        if not member.guild:
            return False

        # Server owner
        if member.id == member.guild.owner_id:

            return True

        # Manual bot owners
        if member.id in BOT_OWNER_IDS:

            return True

        # discord.py owner check
        try:

            if await self.bot.is_owner(member):

                return True

        except Exception as e:

            print(
                "[SECURITY] BOT OWNER CHECK ERROR:",
                repr(e)
            )

        return False


    # ========================================================
    # PROTECTED MEMBER
    # ========================================================

    async def is_protected_member(self, member):

        if not member:
            return False

        if not member.guild:
            return False

        # Server owner
        if member.id == member.guild.owner_id:

            return True

        # Manual bot owner
        if member.id in BOT_OWNER_IDS:

            return True

        # discord.py owner
        try:

            if await self.bot.is_owner(member):

                return True

        except Exception:
            pass

        return False


    # ========================================================
    # STATUS
    # ========================================================

    def status(self, value):

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

        # ----------------------------------------------------
        # INTRO
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # EACH SECURITY
        # ----------------------------------------------------

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

        await asyncio.sleep(
            5
        )

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
    async def antinukeenable(self, ctx):

        if not await self.is_owner(
            ctx.author
        ):

            return await ctx.send(
                "❌ **Only the server owner or bot owner can use this.**",
                delete_after=5
            )

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
    async def antinukedisable(self, ctx):

        if not await self.is_owner(
            ctx.author
        ):

            return await ctx.send(
                "❌ **Only the server owner or bot owner can use this.**",
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
    async def automodstatus(self, ctx):

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
                "❌ **Only the server owner or bot owner can use this.**",
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

        if not await self.is_owner(
            ctx.author
        ):

            return await ctx.send(
                "❌ **Only the server owner or bot owner can use this.**",
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
    # STRICT ANTI-BOT
    # ========================================================
    #
    # ONLY SERVER OWNER MAY ADD BOTS.
    #
    # Bot Owner is NOT allowed to add bots unless they
    # are also the SERVER OWNER.
    #
    # Unauthorized:
    #   1. Bot kicked
    #   2. Inviter removable roles removed
    #
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ):

        # ----------------------------------------------------
        # ONLY BOTS
        # ----------------------------------------------------

        if not member.bot:
            return

        guild = member.guild

        settings = self.get_settings(
            guild.id
        )

        # ----------------------------------------------------
        # ANTI-BOT DISABLED
        # ----------------------------------------------------

        if not settings.get(
            "antibot",
            True
        ):

            print(
                f"[SECURITY] Anti-Bot disabled "
                f"in {guild.name}"
            )

            return

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

        # ----------------------------------------------------
        # FIND INVITER
        # ----------------------------------------------------

        inviter = None

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

                    # Audit entry must be recent
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
        # ONLY SERVER OWNER IS ALLOWED
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
        # EVERYONE ELSE = UNAUTHORIZED
        # ====================================================

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

        print(
            f"[SECURITY] 👑 Server Owner ID: "
            f"{guild.owner_id}"
        )

        # ----------------------------------------------------
        # FETCH INVITER MEMBER
        # ----------------------------------------------------

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

        # ====================================================
        # KICK BOT FIRST
        # ====================================================

        await self.kick_unauthorized_bot(
            member
        )

        # ====================================================
        # REMOVE INVITER ROLES
        # ====================================================

        if inviter_member:

            await self.remove_inviter_roles(
                inviter_member
            )

        else:

            print(
                "[SECURITY] ❌ Inviter member "
                "object unavailable."
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

        # ----------------------------------------------------
        # PERMISSION
        # ----------------------------------------------------

        if not me.guild_permissions.kick_members:

            print(
                "[SECURITY] ❌ KICK FAILED"
            )

            print(
                "[SECURITY] HSL-CORP does not have "
                "`Kick Members` permission."
            )

            return False

        # ----------------------------------------------------
        # ROLE HIERARCHY
        # ----------------------------------------------------

        print(
            f"[SECURITY] HSL top role: "
            f"{me.top_role} "
            f"({me.top_role.position})"
        )

        print(
            f"[SECURITY] Target bot top role: "
            f"{member.top_role} "
            f"({member.top_role.position})"
        )

        if member.id == self.bot.user.id:

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

        # ----------------------------------------------------
        # KICK
        # ----------------------------------------------------

        try:

            await member.kick(
                reason=(
                    "HSL-CORP Security - "
                    "Only server owner can add bots"
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

        # ----------------------------------------------------
        # NEVER REMOVE SERVER OWNER ROLES
        # ----------------------------------------------------

        if member.id == guild.owner_id:

            print(
                "[SECURITY] Server owner → "
                "roles protected."
            )

            return

        # ----------------------------------------------------
        # PROTECTED BOT OWNERS
        #
        # NOTE:
        # For STRICT OWNER-ONLY BOT ADDITION,
        # BOT_OWNER_IDS do NOT get protection here
        # when they add a bot.
        # ----------------------------------------------------

        me = guild.me

        if me is None:

            return

        # ----------------------------------------------------
        # MANAGE ROLES
        # ----------------------------------------------------

        if not me.guild_permissions.manage_roles:

            print(
                "[SECURITY] ❌ ROLE REMOVE FAILED"
            )

            print(
                "[SECURITY] HSL-CORP does not have "
                "`Manage Roles` permission."
            )

            return

        # ----------------------------------------------------
        # ROLE INFORMATION
        # ----------------------------------------------------

        print(
            f"[SECURITY] 🎭 Inviter: "
            f"{member}"
        )

        print(
            f"[SECURITY] Inviter top role: "
            f"{member.top_role} "
            f"({member.top_role.position})"
        )

        print(
            f"[SECURITY] HSL top role: "
            f"{me.top_role} "
            f"({me.top_role.position})"
        )

        # ----------------------------------------------------
        # FIND REMOVABLE ROLES
        # ----------------------------------------------------

        removable_roles = []

        for role in member.roles:

            # @everyone
            if role.is_default():
                continue

            # Managed/integration role
            if role.managed:
                continue

            # HSL cannot manage equal/higher roles
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

        # ----------------------------------------------------
        # NOTHING TO REMOVE
        # ----------------------------------------------------

        if not removable_roles:

            print(
                "[SECURITY] ⚠️ No removable roles."
            )

            return

        # ----------------------------------------------------
        # REMOVE ROLES
        # ----------------------------------------------------

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
                # SERVER OWNER
                # --------------------------------------------

                if message.author.id == message.guild.owner_id:

                    await self.bot.process_commands(
                        message
                    )

                    return

                # --------------------------------------------
                # BOT OWNER
                # --------------------------------------------

                if message.author.id in BOT_OWNER_IDS:

                    await self.bot.process_commands(
                        message
                    )

                    return

                # --------------------------------------------
                # DISCORD.PY OWNER
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
                # MUSIC COMMAND
                # --------------------------------------------

                is_music_command = (

                    content.startswith("!play")
                    or
                    content.startswith("/play")
                    or
                    content.startswith("!p ")
                    or
                    content.startswith("/p ")
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
            "👑 STRICT ANTI-BOT: SERVER OWNER ONLY"
        )

        print(
            f"🤖 Manual Bot Owners: "
            f"{len(BOT_OWNER_IDS)}"
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