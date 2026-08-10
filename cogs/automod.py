
import asyncio
import re
import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


class AutoMod(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # =====================================================
        # MEMORY
        # =====================================================

        self.message_history = defaultdict(
            lambda: deque(maxlen=20)
        )

        self.last_messages = {}
        self.duplicate_counts = defaultdict(int)

        # =====================================================
        # SETTINGS
        # =====================================================

        self.settings = defaultdict(
            lambda: {
                "links": True,
                "spam": True,
                "duplicates": True,
                "badwords": True
            }
        )

        # =====================================================
        # LINK DETECTION
        # =====================================================

        self.link_pattern = re.compile(
            r"(https?://\S+|"
            r"www\.\S+|"
            r"discord\.gg/\S+|"
            r"discord\.com/invite/\S+)",
            re.IGNORECASE
        )

        # =====================================================
        # BAD WORDS
        # =====================================================

        self.bad_words = {
            "mc",
            "randi",
            "maderchod",
            "chakka",
            "bhenchod",
            "bhosdika",
            "chutiye",
            "bsdk",
            "gand",
            "gand mara",
            "muh me lele",
            "teri maa chod dunga",
            "tun chakka hai",
            "bc",
            "bhosdike"
        }

        # =====================================================
        # LIMITS
        # =====================================================

        self.max_messages = 5
        self.time_window = 5
        self.max_duplicates = 3

        # AutoMod timeout
        self.automod_timeout_minutes = 10

    # =========================================================
    # SERVER OWNER BYPASS
    # =========================================================

    def is_server_owner(self, message):

        return (
            message.guild is not None
            and message.guild.owner_id == message.author.id
        )

    # =========================================================
    # TIMEOUT
    # =========================================================

    async def timeout_member(
        self,
        member,
        reason
    ):

        try:

            await member.timeout(
                timedelta(
                    minutes=self.automod_timeout_minutes
                ),
                reason=reason
            )

            return True

        except discord.Forbidden:

            print(
                f"[AUTOMOD] Cannot timeout {member}"
            )

            return False

        except Exception as e:

            print(
                f"[AUTOMOD] Timeout error: {e}"
            )

            return False

    # =========================================================
    # SECURITY EMBED
    # =========================================================

    def security_embed(
        self,
        title,
        description,
        color
    ):

        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )

        embed.set_footer(
            text="HSL SECURITY • AutoMod Protection"
        )

        return embed

    # =========================================================
    # LOAD DATABASE
    # =========================================================

    @commands.Cog.listener()
    async def on_ready(self):

        for guild in self.bot.guilds:

            try:

                row = self.bot.db.get_guild(
                    guild.id
                )

                if row:

                    self.settings[guild.id][
                        "links"
                    ] = bool(
                        row["automod_links"]
                    )

                    self.settings[guild.id][
                        "spam"
                    ] = bool(
                        row["automod_spam"]
                    )

                    self.settings[guild.id][
                        "duplicates"
                    ] = bool(
                        row["automod_duplicates"]
                    )

            except Exception as e:

                print(
                    f"[AUTOMOD] Database error: {e}"
                )

        print(
            "💾 AutoMod settings loaded"
        )

    # =========================================================
    # MAIN MESSAGE LISTENER
    # =========================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        # Ignore bots
        if message.author.bot:
            return

        # Ignore DMs
        if message.guild is None:
            return

        # Server owner bypass
        if self.is_server_owner(message):
            return

        # Moderators bypass
        if message.author.guild_permissions.manage_messages:
            return

        settings = self.settings[
            message.guild.id
        ]

        # =====================================================
        # ANTI-LINK
        # =====================================================

        if settings["links"]:

            if self.link_pattern.search(
                message.content
            ):

                try:
                    await message.delete()
                except Exception:
                    pass

                timed_out = await self.timeout_member(
                    message.author,
                    "HSL AutoMod: Unauthorized link"
                )

                if timed_out:

                    embed = self.security_embed(
                        "🔗 LINK BLOCKED",
                        (
                            f"### 🛡️ Security Action\n\n"
                            f"👤 **Member:** "
                            f"{message.author.mention}\n\n"
                            f"🔗 **Violation:** "
                            f"Unauthorized link\n\n"
                            f"🟢 **Action:** "
                            f"10 Minute Timeout\n\n"
                            f"🗑️ **Message:** Deleted"
                        ),
                        discord.Color.red()
                    )

                    embed.set_thumbnail(
                        url=message.author.display_avatar.url
                    )

                    await message.channel.send(
                        embed=embed,
                        delete_after=7
                    )

                return

        # =====================================================
        # BAD WORD
        # =====================================================

        if settings["badwords"]:

            content = (
                message.content
                .lower()
                .strip()
            )

            found_word = None

            for word in self.bad_words:

                if word in content:

                    found_word = word
                    break

            if found_word:

                try:
                    await message.delete()
                except Exception:
                    pass

                timed_out = await self.timeout_member(
                    message.author,
                    "HSL AutoMod: Inappropriate language"
                )

                if timed_out:

                    embed = self.security_embed(
                        "🚨 LANGUAGE VIOLATION",
                        (
                            f"### 🛡️ Security Action\n\n"
                            f"👤 **Member:** "
                            f"{message.author.mention}\n\n"
                            f"⚠️ **Violation:** "
                            f"Inappropriate language\n\n"
                            f"🟢 **Action:** "
                            f"10 Minute Timeout\n\n"
                            f"🗑️ **Message:** Deleted"
                        ),
                        discord.Color.red()
                    )

                    embed.set_thumbnail(
                        url=message.author.display_avatar.url
                    )

                    await message.channel.send(
                        embed=embed,
                        delete_after=7
                    )

                return

        # =====================================================
        # ANTI-SPAM
        # =====================================================

        if settings["spam"]:

            user_id = message.author.id
            now = time.monotonic()

            history = self.message_history[
                user_id
            ]

            history.append(now)

            while (
                history
                and now - history[0]
                > self.time_window
            ):

                history.popleft()

            if len(history) >= self.max_messages:

                try:
                    await message.delete()
                except Exception:
                    pass

                timed_out = await self.timeout_member(
                    message.author,
                    "HSL AutoMod: Spam"
                )

                if timed_out:

                    embed = self.security_embed(
                        "🚨 SPAM DETECTED",
                        (
                            f"### 🛡️ Security Action\n\n"
                            f"👤 **Member:** "
                            f"{message.author.mention}\n\n"
                            f"📊 **Violation:** "
                            f"Message spam\n\n"
                            f"🟢 **Action:** "
                            f"10 Minute Timeout\n\n"
                            f"📈 **Limit:** "
                            f"5 messages / 5 seconds"
                        ),
                        discord.Color.red()
                    )

                    embed.set_thumbnail(
                        url=message.author.display_avatar.url
                    )

                    await message.channel.send(
                        embed=embed,
                        delete_after=7
                    )

                history.clear()

                return

        # =====================================================
        # ANTI-DUPLICATE
        # =====================================================

        if settings["duplicates"]:

            user_id = message.author.id

            content = (
                message.content
                .strip()
                .lower()
            )

            if (
                content
                and self.last_messages.get(
                    user_id
                ) == content
            ):

                self.duplicate_counts[
                    user_id
                ] += 1

                if (
                    self.duplicate_counts[
                        user_id
                    ] >= self.max_duplicates
                ):

                    try:
                        await message.delete()
                    except Exception:
                        pass

                    timed_out = (
                        await self.timeout_member(
                            message.author,
                            "HSL AutoMod: Repeated messages"
                        )
                    )

                    if timed_out:

                        embed = self.security_embed(
                            "🔁 REPEATED MESSAGE",
                            (
                                f"### 🛡️ Security Action\n\n"
                                f"👤 **Member:** "
                                f"{message.author.mention}\n\n"
                                f"⚠️ **Violation:** "
                                f"Repeated message\n\n"
                                f"🟢 **Action:** "
                                f"10 Minute Timeout\n\n"
                                f"🔢 **Limit:** "
                                f"3 repeated messages"
                            ),
                            discord.Color.red()
                        )

                        embed.set_thumbnail(
                            url=message.author.display_avatar.url
                        )

                        await message.channel.send(
                            embed=embed,
                            delete_after=7
                        )

                    self.duplicate_counts[
                        user_id
                    ] = 0

                    return

            else:

                self.duplicate_counts[
                    user_id
                ] = 0

            self.last_messages[
                user_id
            ] = content

    # =========================================================
    # STATUS
    # =========================================================

    @app_commands.command(
        name="automod_status",
        description="Show AutoMod security status"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def automod_status(
        self,
        interaction: discord.Interaction
    ):

        settings = self.settings[
            interaction.guild.id
        ]

        def status(value):

            return (
                "🟢 **ONLINE**"
                if value
                else "🔴 **OFFLINE**"
            )

        embed = discord.Embed(
            title="🛡️ HSL SECURITY",
            description=(
                "### SECURITY STATUS\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="🔗 Anti-Link",
            value=status(
                settings["links"]
            ),
            inline=True
        )

        embed.add_field(
            name="🚨 Anti-Spam",
            value=status(
                settings["spam"]
            ),
            inline=True
        )

        embed.add_field(
            name="🔁 Anti-Duplicate",
            value=status(
                settings["duplicates"]
            ),
            inline=True
        )

        embed.add_field(
            name="🤬 Anti-Badword",
            value=status(
                settings["badwords"]
            ),
            inline=True
        )

        embed.add_field(
            name="🔇 Auto Timeout",
            value="🟢 **10 MINUTES**",
            inline=True
        )

        embed.add_field(
            name="👑 Owner",
            value="🟢 **BYPASS**",
            inline=True
        )

        embed.set_footer(
            text="HSL SECURITY • Protection System"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =========================================================
    # ANTI NUKE ENABLE
    # =========================================================

    @app_commands.command(
        name="antinukeenable",
        description="Enable all security systems"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def antinukeenable(
        self,
        interaction: discord.Interaction
    ):

        guild_id = interaction.guild.id

        # -----------------------------------------------------
        # START MESSAGE
        # -----------------------------------------------------

        embed = discord.Embed(
            title="🛡️ HSL SECURITY",
            description=(
                "# 🟢 SECURITY BOOTING\n\n"
                "### 🟢\n"
                "**Initializing protection...**\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="HSL SECURITY • Initializing"
        )

        await interaction.response.send_message(
            embed=embed
        )

        message = (
            await interaction.original_response()
        )

        # -----------------------------------------------------
        # BIG GREEN CIRCLE ANIMATION
        # -----------------------------------------------------

        frames = [
            "🟢",
            "🟢 🟢",
            "🟢 🟢 🟢",
            "🟢 🟢 🟢 🟢",
            "🟢 🟢 🟢",
            "🟢 🟢",
            "🟢"
        ]

        for frame in frames:

            embed.description = (
                "# 🟢 SECURITY BOOTING\n\n"
                f"## {frame}\n"
                "**Initializing protection...**\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )

            await message.edit(
                embed=embed
            )

            await asyncio.sleep(0.25)

        # -----------------------------------------------------
        # ANTI LINK
        # -----------------------------------------------------

        embed.description = (
            "# 🛡️ SECURITY BOOTING\n\n"
            "## 🟢\n"
            "🟢 **Anti-Link**\n"
            "🔄 Loading..."
        )

        await message.edit(embed=embed)

        await asyncio.sleep(0.7)

        # -----------------------------------------------------
        # SPAM
        # -----------------------------------------------------

        embed.description = (
            "# 🛡️ SECURITY BOOTING\n\n"
            "## 🟢\n"
            "✅ **Anti-Link**\n"
            "🟢 **Anti-Spam**\n"
            "🔄 Loading..."
        )

        await message.edit(embed=embed)

        await asyncio.sleep(0.7)

        # -----------------------------------------------------
        # DUPLICATE
        # -----------------------------------------------------

        embed.description = (
            "# 🛡️ SECURITY BOOTING\n\n"
            "## 🟢\n"
            "✅ **Anti-Link**\n"
            "✅ **Anti-Spam**\n"
            "🟢 **Anti-Duplicate**\n"
            "🔄 Loading..."
        )

        await message.edit(embed=embed)

        await asyncio.sleep(0.7)

        # -----------------------------------------------------
        # BADWORD
        # -----------------------------------------------------

        embed.description = (
            "# 🛡️ SECURITY BOOTING\n\n"
            "## 🟢\n"
            "✅ **Anti-Link**\n"
            "✅ **Anti-Spam**\n"
            "✅ **Anti-Duplicate**\n"
            "🟢 **Anti-Badword**\n"
            "🔄 Loading..."
        )

        await message.edit(embed=embed)

        await asyncio.sleep(0.7)

        # -----------------------------------------------------
        # ENABLE ALL
        # -----------------------------------------------------

        self.settings[
            guild_id
        ]["links"] = True

        self.settings[
            guild_id
        ]["spam"] = True

        self.settings[
            guild_id
        ]["duplicates"] = True

        self.settings[
            guild_id
        ]["badwords"] = True

        # Database
        self.bot.db.set_automod(
            guild_id,
            "links",
            True
        )

        self.bot.db.set_automod(
            guild_id,
            "spam",
            True
        )

        self.bot.db.set_automod(
            guild_id,
            "duplicates",
            True
        )

        await asyncio.sleep(0.5)

        # -----------------------------------------------------
        # FINAL ONLINE
        # -----------------------------------------------------

        embed = discord.Embed(
            title="🛡️ HSL SECURITY",
            description=(
                "# 🟢 SECURITY ONLINE\n\n"
                "## 🟢\n\n"
                "✅ 🔗 **ANTI-LINK**\n"
                "✅ 🚨 **ANTI-SPAM**\n"
                "✅ 🔁 **ANTI-DUPLICATE**\n"
                "✅ 🤬 **ANTI-BADWORD**\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "### 🟢 PROTECTION ACTIVE\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="HSL SECURITY • All Systems Online"
        )

        await message.edit(
            embed=embed
        )

        # -----------------------------------------------------
        # DELETE AFTER 5 SECONDS
        # -----------------------------------------------------

        await asyncio.sleep(5)

        try:
            await message.delete()
        except Exception:
            pass

    # =========================================================
    # ANTI NUKE DISABLE
    # =========================================================

    @app_commands.command(
        name="antinukedisable",
        description="Disable all security systems"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def antinukedisable(
        self,
        interaction: discord.Interaction
    ):

        guild_id = interaction.guild.id

        # -----------------------------------------------------
        # START
        # -----------------------------------------------------

        embed = discord.Embed(
            title="🛡️ HSL SECURITY",
            description=(
                "# 🔴 SECURITY SHUTDOWN\n\n"
                "## 🔴\n"
                "**Disabling protection...**\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.red()
        )

        embed.set_footer(
            text="HSL SECURITY • Shutting Down"
        )

        await interaction.response.send_message(
            embed=embed
        )

        message = (
            await interaction.original_response()
        )

        # -----------------------------------------------------
        # BIG RED CIRCLE ANIMATION
        # -----------------------------------------------------

        frames = [
            "🔴",
            "🔴 🔴",
            "🔴 🔴 🔴",
            "🔴 🔴 🔴 🔴",
            "🔴 🔴 🔴",
            "🔴 🔴",
            "🔴"
        ]

        for frame in frames:

            embed.description = (
                "# 🔴 SECURITY SHUTDOWN\n\n"
                f"## {frame}\n"
                "**Disabling protection...**\n\n"
                "━━━━━━━━━━━━━━━━━━━━"
            )

            await message.edit(
                embed=embed
            )

            await asyncio.sleep(0.25)

        # -----------------------------------------------------
        # LINK
        # -----------------------------------------------------

        embed.description = (
            "# 🔴 SECURITY SHUTDOWN\n\n"
            "## 🔴\n"
            "🔴 **Anti-Link**\n"
            "🔄 Disabling..."
        )

        await message.edit(embed=embed)

        await asyncio.sleep(0.7)

        # -----------------------------------------------------
        # SPAM
        # -----------------------------------------------------

        embed.description = (
            "# 🔴 SECURITY SHUTDOWN\n\n"
            "## 🔴\n"
            "❌ **Anti-Link**\n"
            "🔴 **Anti-Spam**\n"
            "🔄 Disabling..."
        )

        await message.edit(embed=embed)

        await asyncio.sleep(0.7)

        # -----------------------------------------------------
        # DUPLICATE
        # -----------------------------------------------------

        embed.description = (
            "# 🔴 SECURITY SHUTDOWN\n\n"
            "## 🔴\n"
            "❌ **Anti-Link**\n"
            "❌ **Anti-Spam**\n"
            "🔴 **Anti-Duplicate**\n"
            "🔄 Disabling..."
        )

        await message.edit(embed=embed)

        await asyncio.sleep(0.7)

        # -----------------------------------------------------
        # BADWORD
        # -----------------------------------------------------

        embed.description = (
            "# 🔴 SECURITY SHUTDOWN\n\n"
            "## 🔴\n"
            "❌ **Anti-Link**\n"
            "❌ **Anti-Spam**\n"
            "❌ **Anti-Duplicate**\n"
            "🔴 **Anti-Badword**\n"
            "🔄 Disabling..."
        )

        await message.edit(embed=embed)

        await asyncio.sleep(0.7)

        # -----------------------------------------------------
        # DISABLE ALL
        # -----------------------------------------------------

        self.settings[
            guild_id
        ]["links"] = False

        self.settings[
            guild_id
        ]["spam"] = False

        self.settings[
            guild_id
        ]["duplicates"] = False

        self.settings[
            guild_id
        ]["badwords"] = False

        # Database
        self.bot.db.set_automod(
            guild_id,
            "links",
            False
        )

        self.bot.db.set_automod(
            guild_id,
            "spam",
            False
        )

        self.bot.db.set_automod(
            guild_id,
            "duplicates",
            False
        )

        await asyncio.sleep(0.5)

        # -----------------------------------------------------
        # FINAL OFFLINE
        # -----------------------------------------------------

        embed = discord.Embed(
            title="🛡️ HSL SECURITY",
            description=(
                "# 🔴 SECURITY OFFLINE\n\n"
                "## 🔴\n\n"
                "❌ 🔗 **ANTI-LINK**\n"
                "❌ 🚨 **ANTI-SPAM**\n"
                "❌ 🔁 **ANTI-DUPLICATE**\n"
                "❌ 🤬 **ANTI-BADWORD**\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "### 🔴 PROTECTION DISABLED\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.red()
        )

        embed.set_footer(
            text="HSL SECURITY • All Systems Offline"
        )

        await message.edit(
            embed=embed
        )

        # -----------------------------------------------------
        # DELETE AFTER 5 SECONDS
        # -----------------------------------------------------

        await asyncio.sleep(5)

        try:
            await message.delete()
        except Exception:
            pass

    # =========================================================
    # INDIVIDUAL ANTI-LINK
    # =========================================================

    @app_commands.command(
        name="automod_links",
        description="Enable or disable Anti-Link"
    )
    @app_commands.describe(
        enabled="True = ON, False = OFF"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def automod_links(
        self,
        interaction: discord.Interaction,
        enabled: bool
    ):

        guild_id = interaction.guild.id

        self.settings[
            guild_id
        ]["links"] = enabled

        self.bot.db.set_automod(
            guild_id,
            "links",
            enabled
        )

        status = (
            "🟢 ENABLED"
            if enabled
            else "🔴 DISABLED"
        )

        await interaction.response.send_message(
            f"🔗 Anti-Link is now **{status}**.",
            ephemeral=True
        )

    # =========================================================
    # INDIVIDUAL SPAM
    # =========================================================

    @app_commands.command(
        name="automod_spam",
        description="Enable or disable Anti-Spam"
    )
    @app_commands.describe(
        enabled="True = ON, False = OFF"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def automod_spam(
        self,
        interaction: discord.Interaction,
        enabled: bool
    ):

        guild_id = interaction.guild.id

        self.settings[
            guild_id
        ]["spam"] = enabled

        self.bot.db.set_automod(
            guild_id,
            "spam",
            enabled
        )

        status = (
            "🟢 ENABLED"
            if enabled
            else "🔴 DISABLED"
        )

        await interaction.response.send_message(
            f"🚨 Anti-Spam is now **{status}**.",
            ephemeral=True
        )

    # =========================================================
    # INDIVIDUAL DUPLICATES
    # =========================================================

    @app_commands.command(
        name="automod_duplicates",
        description="Enable or disable Anti-Duplicate"
    )
    @app_commands.describe(
        enabled="True = ON, False = OFF"
    )
    @app_commands.checks.has_permissions(
        administrator=True
    )
    async def automod_duplicates(
        self,
        interaction: discord.Interaction,
        enabled: bool
    ):

        guild_id = interaction.guild.id

        self.settings[
            guild_id
        ]["duplicates"] = enabled

        self.bot.db.set_automod(
            guild_id,
            "duplicates",
            enabled
        )

        status = (
            "🟢 ENABLED"
            if enabled
            else "🔴 DISABLED"
        )

        await interaction.response.send_message(
            f"🔁 Anti-Duplicate is now **{status}**.",
            ephemeral=True
        )


# =============================================================
# SETUP
# =============================================================

async def setup(bot):

    await bot.add_cog(
        AutoMod(bot)
    )

