
import sqlite3
from datetime import timedelta

import discord
from discord.ext import commands
from discord import app_commands


class Warnings(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.db = sqlite3.connect("bot.db")
        self.cursor = self.db.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL
            )
        """)

        self.db.commit()

        # 3 warnings = automatic timeout
        self.warning_limit = 3

        # Automatic timeout duration
        self.auto_timeout_minutes = 10

    # =========================================================
    # LOG
    # =========================================================

    async def send_log(self, guild, embed):

        logging_cog = self.bot.get_cog("Logging")

        if logging_cog:
            try:
                await logging_cog.send_log(
                    guild,
                    embed
                )
            except Exception as e:
                print(f"[WARNINGS] Logging error: {e}")

    # =========================================================
    # WARN
    # =========================================================

    @commands.hybrid_command(
        name="warn",
        description="Warn a member"
    )
    @app_commands.describe(
        member="Member to warn",
        reason="Reason for warning"
    )
    @commands.has_permissions(
        moderate_members=True
    )
    async def warn(
        self,
        ctx,
        member: discord.Member,
        *,
        reason: str = "No reason provided"
    ):

        if member == ctx.author:
            return await ctx.send(
                "❌ You cannot warn yourself.",
                delete_after=5
            )

        if member.bot:
            return await ctx.send(
                "❌ You cannot warn a bot.",
                delete_after=5
            )

        # Moderator role check
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(
                "❌ You cannot warn a member with an equal or higher role.",
                delete_after=5
            )

        # Bot role check
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(
                "❌ I cannot moderate this member because their role is equal to or higher than mine.",
                delete_after=5
            )

        # =====================================================
        # ADD WARNING
        # =====================================================

        self.cursor.execute(
            """
            INSERT INTO warnings
            (guild_id, user_id, moderator_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            (
                ctx.guild.id,
                member.id,
                ctx.author.id,
                reason
            )
        )

        self.db.commit()

        # =====================================================
        # COUNT WARNINGS
        # =====================================================

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM warnings
            WHERE guild_id = ?
            AND user_id = ?
            """,
            (
                ctx.guild.id,
                member.id
            )
        )

        total = self.cursor.fetchone()[0]

        # =====================================================
        # 3 WARNINGS = AUTOMATIC TIMEOUT
        # =====================================================

        if total >= self.warning_limit:

            try:

                await member.timeout(
                    timedelta(
                        minutes=self.auto_timeout_minutes
                    ),
                    reason="Automatic timeout: 3 warnings reached"
                )

                embed = discord.Embed(
                    title="🔇 AUTOMATIC TIMEOUT",
                    description=(
                        f"{member.mention} reached "
                        f"**{self.warning_limit} warnings**.\n\n"
                        f"⏱️ Timeout: **"
                        f"{self.auto_timeout_minutes} minutes**"
                    ),
                    color=discord.Color.red()
                )

                embed.set_thumbnail(
                    url=member.display_avatar.url
                )

                embed.add_field(
                    name="👤 Member",
                    value=member.mention,
                    inline=True
                )

                embed.add_field(
                    name="⚠️ Warnings",
                    value=f"{total} / {self.warning_limit}",
                    inline=True
                )

                embed.add_field(
                    name="🔇 Action",
                    value=f"{self.auto_timeout_minutes} Minutes",
                    inline=True
                )

                embed.add_field(
                    name="📝 Reason",
                    value=reason,
                    inline=False
                )

                embed.add_field(
                    name="🛡️ Moderator",
                    value=ctx.author.mention,
                    inline=True
                )

                embed.set_footer(
                    text="HSL SECURITY • Automatic Moderation"
                )

                await ctx.send(
                    embed=embed
                )

                # =================================================
                # LOG
                # =================================================

                log_embed = discord.Embed(
                    title="🔇 AUTOMATIC TIMEOUT",
                    description=(
                        f"{member.mention} reached "
                        f"**{self.warning_limit} warnings** "
                        "and was automatically timed out."
                    ),
                    color=discord.Color.red()
                )

                log_embed.set_thumbnail(
                    url=member.display_avatar.url
                )

                log_embed.add_field(
                    name="👤 User",
                    value=member.mention,
                    inline=True
                )

                log_embed.add_field(
                    name="🛡️ Moderator",
                    value=ctx.author.mention,
                    inline=True
                )

                log_embed.add_field(
                    name="⚠️ Warnings",
                    value=str(total),
                    inline=True
                )

                log_embed.add_field(
                    name="⏱️ Timeout",
                    value=f"{self.auto_timeout_minutes} minutes",
                    inline=True
                )

                log_embed.add_field(
                    name="📝 Reason",
                    value=reason,
                    inline=False
                )

                log_embed.set_footer(
                    text="HSL SECURITY • Warning System"
                )

                await self.send_log(
                    ctx.guild,
                    log_embed
                )

                # =================================================
                # RESET WARNINGS AFTER TIMEOUT
                # =================================================

                self.cursor.execute(
                    """
                    DELETE FROM warnings
                    WHERE guild_id = ?
                    AND user_id = ?
                    """,
                    (
                        ctx.guild.id,
                        member.id
                    )
                )

                self.db.commit()

            except discord.Forbidden:

                await ctx.send(
                    (
                        "❌ Warning added, but I couldn't "
                        "timeout this member.\n"
                        "Check my **Moderate Members** permission "
                        "and role position."
                    ),
                    delete_after=8
                )

            except Exception as e:

                print(
                    f"[WARNINGS] Automatic timeout error: {e}"
                )

                await ctx.send(
                    "❌ Warning added, but automatic timeout failed.",
                    delete_after=7
                )

            return

        # =====================================================
        # NORMAL WARNING EMBED
        # =====================================================

        embed = discord.Embed(
            title="⚠️ WARNING ISSUED",
            description=(
                f"{member.mention} received "
                f"**Warning #{total}**."
            ),
            color=discord.Color.orange()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="👤 Member",
            value=member.mention,
            inline=True
        )

        embed.add_field(
            name="⚠️ Warnings",
            value=f"{total} / {self.warning_limit}",
            inline=True
        )

        embed.add_field(
            name="🛡️ Moderator",
            value=ctx.author.mention,
            inline=True
        )

        embed.add_field(
            name="📝 Reason",
            value=reason,
            inline=False
        )

        embed.add_field(
            name="⚡ Next Action",
            value=(
                f"{self.warning_limit} warnings → "
                f"**{self.auto_timeout_minutes} minute timeout**"
            ),
            inline=False
        )

        embed.set_footer(
            text="HSL SECURITY • Warning System"
        )

        await ctx.send(
            embed=embed
        )

        # =====================================================
        # LOG NORMAL WARNING
        # =====================================================

        log_embed = discord.Embed(
            title="⚠️ WARNING ISSUED",
            description=(
                f"{member.mention} received "
                f"**Warning #{total}**."
            ),
            color=discord.Color.orange()
        )

        log_embed.set_thumbnail(
            url=member.display_avatar.url
        )

        log_embed.add_field(
            name="👤 User",
            value=member.mention,
            inline=True
        )

        log_embed.add_field(
            name="🛡️ Moderator",
            value=ctx.author.mention,
            inline=True
        )

        log_embed.add_field(
            name="⚠️ Warnings",
            value=f"{total} / {self.warning_limit}",
            inline=True
        )

        log_embed.add_field(
            name="📝 Reason",
            value=reason,
            inline=False
        )

        log_embed.set_footer(
            text="HSL SECURITY • Warning System"
        )

        await self.send_log(
            ctx.guild,
            log_embed
        )

    # =========================================================
    # WARNINGS
    # =========================================================

    @commands.hybrid_command(
        name="warnings",
        description="View a member's warnings"
    )
    @app_commands.describe(
        member="Member whose warnings you want to see"
    )
    @commands.has_permissions(
        moderate_members=True
    )
    async def warnings(
        self,
        ctx,
        member: discord.Member
    ):

        self.cursor.execute(
            """
            SELECT id, moderator_id, reason
            FROM warnings
            WHERE guild_id = ?
            AND user_id = ?
            ORDER BY id DESC
            """,
            (
                ctx.guild.id,
                member.id
            )
        )

        records = self.cursor.fetchall()

        if not records:
            return await ctx.send(
                f"✅ {member.mention} has no warnings.",
                delete_after=5
            )

        embed = discord.Embed(
            title=f"⚠️ WARNINGS — {member}",
            color=discord.Color.orange()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        for warning_id, moderator_id, reason in records[:10]:

            moderator = ctx.guild.get_member(
                moderator_id
            )

            moderator_name = (
                moderator.mention
                if moderator
                else f"Unknown (`{moderator_id}`)"
            )

            embed.add_field(
                name=f"⚠️ Warning #{warning_id}",
                value=(
                    f"**Reason:** {reason}\n"
                    f"**Moderator:** {moderator_name}"
                ),
                inline=False
            )

        if len(records) > 10:
            embed.set_footer(
                text=f"Showing 10 of {len(records)} warnings"
            )
        else:
            embed.set_footer(
                text=f"Total warnings: {len(records)}"
            )

        await ctx.send(
            embed=embed
        )

    # =========================================================
    # UNWARN
    # =========================================================

    @commands.hybrid_command(
        name="unwarn",
        description="Remove a warning"
    )
    @app_commands.describe(
        warning_id="Warning ID to remove"
    )
    @commands.has_permissions(
        moderate_members=True
    )
    async def unwarn(
        self,
        ctx,
        warning_id: int
    ):

        self.cursor.execute(
            """
            SELECT id, user_id
            FROM warnings
            WHERE id = ?
            AND guild_id = ?
            """,
            (
                warning_id,
                ctx.guild.id
            )
        )

        warning = self.cursor.fetchone()

        if not warning:
            return await ctx.send(
                "❌ Warning not found.",
                delete_after=5
            )

        self.cursor.execute(
            """
            DELETE FROM warnings
            WHERE id = ?
            AND guild_id = ?
            """,
            (
                warning_id,
                ctx.guild.id
            )
        )

        self.db.commit()

        embed = discord.Embed(
            title="✅ WARNING REMOVED",
            description=(
                f"Warning `#{warning_id}` "
                "has been removed."
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text=f"Removed by {ctx.author}"
        )

        await ctx.send(
            embed=embed
        )


# =============================================================
# SETUP
# =============================================================

async def setup(bot):
    await bot.add_cog(Warnings(bot))

