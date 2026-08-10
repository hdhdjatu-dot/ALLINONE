
import sqlite3
import discord
from discord.ext import commands


# ============================================================
# HSL WELCOME SYSTEM
# PER-SERVER SETTINGS
# ============================================================

class Welcome(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # ====================================================
        # DATABASE
        # ====================================================

        self.db = sqlite3.connect("bot.db")
        self.cursor = self.db.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS welcome_settings (
                guild_id INTEGER PRIMARY KEY,

                welcome_channel_id INTEGER,
                goodbye_channel_id INTEGER,

                auto_role_id INTEGER,

                banner_gif TEXT,

                welcome_message TEXT,
                goodbye_message TEXT,

                enabled INTEGER DEFAULT 1
            )
        """)

        self.db.commit()

        # Default HSL GIF
        self.default_gif = (
            "https://media3.giphy.com/media/"
            "v1.Y2lkPTc5MGI3NjExZ3RqemR3c3A0MHl3NWw1NHE4a2FjdWVkdDdqdXppaXdxdHhobGF5ayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/"
            "iBILBPeCHDVuELjOND/giphy.gif"
        )

        self.default_welcome = (
            "Welcome {user}!\n\n"
            "🎉 We're glad to have you join our community.\n\n"
            "💬 Join the conversations\n"
            "🎮 Enjoy your stay\n"
            "🎁 Participate in events\n\n"
            "👥 Member #{count}\n\n"
            "🔥 Together We Rise."
        )

        self.default_goodbye = (
            "**{username}** has left the server.\n\n"
            "👥 Members Remaining: {count}\n\n"
            "🔥 Once HSL, Always HSL."
        )

    # ========================================================
    # GET / CREATE SETTINGS
    # ========================================================

    def get_settings(self, guild_id):

        self.cursor.execute(
            """
            SELECT
                welcome_channel_id,
                goodbye_channel_id,
                auto_role_id,
                banner_gif,
                welcome_message,
                goodbye_message,
                enabled
            FROM welcome_settings
            WHERE guild_id = ?
            """,
            (guild_id,)
        )

        row = self.cursor.fetchone()

        if row:

            return {
                "welcome_channel_id": row[0],
                "goodbye_channel_id": row[1],
                "auto_role_id": row[2],
                "banner_gif": row[3] or self.default_gif,
                "welcome_message": row[4] or self.default_welcome,
                "goodbye_message": row[5] or self.default_goodbye,
                "enabled": bool(row[6])
            }

        # Create default settings
        self.cursor.execute(
            """
            INSERT INTO welcome_settings (
                guild_id,
                welcome_channel_id,
                goodbye_channel_id,
                auto_role_id,
                banner_gif,
                welcome_message,
                goodbye_message,
                enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                None,
                None,
                None,
                self.default_gif,
                self.default_welcome,
                self.default_goodbye,
                1
            )
        )

        self.db.commit()

        return {
            "welcome_channel_id": None,
            "goodbye_channel_id": None,
            "auto_role_id": None,
            "banner_gif": self.default_gif,
            "welcome_message": self.default_welcome,
            "goodbye_message": self.default_goodbye,
            "enabled": True
        }

    # ========================================================
    # UPDATE SETTING
    # ========================================================

    def update_setting(
        self,
        guild_id,
        column,
        value
    ):

        allowed = {
            "welcome_channel_id",
            "goodbye_channel_id",
            "auto_role_id",
            "banner_gif",
            "welcome_message",
            "goodbye_message",
            "enabled"
        }

        if column not in allowed:
            return

        self.get_settings(guild_id)

        self.cursor.execute(
            f"""
            UPDATE welcome_settings
            SET {column} = ?
            WHERE guild_id = ?
            """,
            (value, guild_id)
        )

        self.db.commit()

    # ========================================================
    # FORMAT MESSAGE
    # ========================================================

    def format_message(
        self,
        message,
        member
    ):

        return (
            message
            .replace("{user}", member.mention)
            .replace("{username}", member.name)
            .replace("{server}", member.guild.name)
            .replace(
                "{count}",
                str(member.guild.member_count)
            )
        )

    # ========================================================
    # READY
    # ========================================================

    @commands.Cog.listener()
    async def on_ready(self):

        print("✅ Per-server Welcome System loaded")

    # ========================================================
    # MEMBER JOIN
    # ========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member: discord.Member
    ):

        settings = self.get_settings(
            member.guild.id
        )

        # ====================================================
        # AUTO ROLE
        # ====================================================

        role_id = settings["auto_role_id"]

        if role_id:

            role = member.guild.get_role(
                role_id
            )

            if role:

                try:

                    await member.add_roles(
                        role,
                        reason="HSL Welcome System - Auto Role"
                    )

                    print(
                        f"✅ Auto role given to {member}"
                    )

                except Exception as e:

                    print(
                        f"❌ Auto Role Error: {e}"
                    )

        # ====================================================
        # WELCOME ENABLED?
        # ====================================================

        if not settings["enabled"]:
            return

        # ====================================================
        # CHANNEL
        # ====================================================

        channel_id = settings[
            "welcome_channel_id"
        ]

        if not channel_id:

            print(
                f"⚠️ Welcome channel not configured "
                f"for {member.guild.name}"
            )

            return

        channel = member.guild.get_channel(
            channel_id
        )

        if not channel:

            print(
                "❌ Welcome channel not found."
            )

            return

        # ====================================================
        # MESSAGE
        # ====================================================

        message = self.format_message(
            settings["welcome_message"],
            member
        )

        # ====================================================
        # EMBED
        # ====================================================

        embed = discord.Embed(

            title=(
                f"👑 Welcome to "
                f"{member.guild.name}"
            ),

            description=message,

            color=0x8A2BE2
        )

        # Avatar
        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        # Server GIF
        if settings["banner_gif"]:

            embed.set_image(
                url=settings["banner_gif"]
            )

        embed.set_footer(
            text=(
                f"{member.guild.name} • "
                "Official Community"
            )
        )

        # ====================================================
        # SEND
        # ====================================================

        try:

            await channel.send(
                content=f"🎉 Welcome {member.mention}!",
                embed=embed
            )

            print(
                f"👋 Welcome sent for {member} "
                f"in {member.guild.name}"
            )

        except Exception as e:

            print(
                f"❌ Welcome send error: {e}"
            )

    # ========================================================
    # MEMBER LEAVE
    # ========================================================

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member: discord.Member
    ):

        settings = self.get_settings(
            member.guild.id
        )

        if not settings["enabled"]:
            return

        # ====================================================
        # GOODBYE CHANNEL
        # ====================================================

        channel_id = settings[
            "goodbye_channel_id"
        ]

        # If goodbye channel isn't configured,
        # use welcome channel.

        if not channel_id:

            channel_id = settings[
                "welcome_channel_id"
            ]

        if not channel_id:

            return

        channel = member.guild.get_channel(
            channel_id
        )

        if not channel:
            return

        # ====================================================
        # MESSAGE
        # ====================================================

        message = self.format_message(
            settings["goodbye_message"],
            member
        )

        # ====================================================
        # EMBED
        # ====================================================

        embed = discord.Embed(

            title="👋 Goodbye",

            description=message,

            color=0xFF5555
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        if settings["banner_gif"]:

            embed.set_image(
                url=settings["banner_gif"]
            )

        embed.set_footer(
            text=(
                f"{member.guild.name} • "
                "HSL & CORPORATION"
            )
        )

        try:

            await channel.send(
                embed=embed
            )

            print(
                f"👋 Goodbye sent for {member}"
            )

        except Exception as e:

            print(
                f"❌ Goodbye error: {e}"
            )

    # ========================================================
    # SET WELCOME CHANNEL
    # ========================================================

    @commands.hybrid_command(
        name="welcomechannel",
        description="Set the welcome channel"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcomechannel(
        self,
        ctx,
        channel: discord.TextChannel
    ):

        self.update_setting(
            ctx.guild.id,
            "welcome_channel_id",
            channel.id
        )

        await ctx.send(
            f"✅ Welcome channel set to {channel.mention}.",
            delete_after=5
        )

    # ========================================================
    # SET GOODBYE CHANNEL
    # ========================================================

    @commands.hybrid_command(
        name="goodbyechannel",
        description="Set the goodbye channel"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def goodbyechannel(
        self,
        ctx,
        channel: discord.TextChannel
    ):

        self.update_setting(
            ctx.guild.id,
            "goodbye_channel_id",
            channel.id
        )

        await ctx.send(
            f"✅ Goodbye channel set to {channel.mention}.",
            delete_after=5
        )

    # ========================================================
    # SET AUTO ROLE
    # ========================================================

    @commands.hybrid_command(
        name="welcomerole",
        description="Set the automatic role"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcomerole(
        self,
        ctx,
        role: discord.Role
    ):

        self.update_setting(
            ctx.guild.id,
            "auto_role_id",
            role.id
        )

        await ctx.send(
            f"✅ Auto role set to {role.mention}.",
            delete_after=5
        )

    # ========================================================
    # REMOVE AUTO ROLE
    # ========================================================

    @commands.hybrid_command(
        name="welcomeroleremove",
        description="Disable automatic role"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcomeroleremove(
        self,
        ctx
    ):

        self.update_setting(
            ctx.guild.id,
            "auto_role_id",
            None
        )

        await ctx.send(
            "✅ Auto role disabled.",
            delete_after=5
        )

    # ========================================================
    # SET GIF
    # ========================================================

    @commands.hybrid_command(
        name="welcomegif",
        description="Set the welcome GIF"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcomegif(
        self,
        ctx,
        url: str
    ):

        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):

            return await ctx.send(
                "❌ Please provide a valid GIF URL.",
                delete_after=5
            )

        self.update_setting(
            ctx.guild.id,
            "banner_gif",
            url
        )

        await ctx.send(
            "✅ Welcome GIF updated.",
            delete_after=5
        )

    # ========================================================
    # RESET GIF
    # ========================================================

    @commands.hybrid_command(
        name="welcomegifreset",
        description="Reset the welcome GIF"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcomegifreset(
        self,
        ctx
    ):

        self.update_setting(
            ctx.guild.id,
            "banner_gif",
            self.default_gif
        )

        await ctx.send(
            "✅ Welcome GIF reset to default.",
            delete_after=5
        )

    # ========================================================
    # SET WELCOME MESSAGE
    # ========================================================

    @commands.hybrid_command(
        name="welcomemessage",
        description="Set the welcome message"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcomemessage(
        self,
        ctx,
        *,
        message: str
    ):

        self.update_setting(
            ctx.guild.id,
            "welcome_message",
            message
        )

        await ctx.send(
            "✅ Welcome message updated.",
            delete_after=5
        )

    # ========================================================
    # SET GOODBYE MESSAGE
    # ========================================================

    @commands.hybrid_command(
        name="goodbyemessage",
        description="Set the goodbye message"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def goodbyemessage(
        self,
        ctx,
        *,
        message: str
    ):

        self.update_setting(
            ctx.guild.id,
            "goodbye_message",
            message
        )

        await ctx.send(
            "✅ Goodbye message updated.",
            delete_after=5
        )

    # ========================================================
    # ENABLE
    # ========================================================

    @commands.hybrid_command(
        name="welcomeenable",
        description="Enable welcome and goodbye system"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcomeenable(
        self,
        ctx
    ):

        self.update_setting(
            ctx.guild.id,
            "enabled",
            1
        )

        await ctx.send(
            "🟢 **Welcome System Enabled**",
            delete_after=5
        )

    # ========================================================
    # DISABLE
    # ========================================================

    @commands.hybrid_command(
        name="welcomedisable",
        description="Disable welcome and goodbye system"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcomedisable(
        self,
        ctx
    ):

        self.update_setting(
            ctx.guild.id,
            "enabled",
            0
        )

        await ctx.send(
            "🔴 **Welcome System Disabled**",
            delete_after=5
        )

    # ========================================================
    # STATUS
    # ========================================================

    @commands.hybrid_command(
        name="welcomestatus",
        description="Show welcome system settings"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def welcomestatus(
        self,
        ctx
    ):

        settings = self.get_settings(
            ctx.guild.id
        )

        welcome_channel = (
            f"<#{settings['welcome_channel_id']}>"
            if settings["welcome_channel_id"]
            else "Not set"
        )

        goodbye_channel = (
            f"<#{settings['goodbye_channel_id']}>"
            if settings["goodbye_channel_id"]
            else "Welcome channel"
        )

        role = (
            f"<@&{settings['auto_role_id']}>"
            if settings["auto_role_id"]
            else "Disabled"
        )

        embed = discord.Embed(
            title="⚙️ Welcome System Settings",
            color=0x8A2BE2
        )

        embed.add_field(
            name="📢 Welcome Channel",
            value=welcome_channel,
            inline=True
        )

        embed.add_field(
            name="👋 Goodbye Channel",
            value=goodbye_channel,
            inline=True
        )

        embed.add_field(
            name="🎭 Auto Role",
            value=role,
            inline=True
        )

        embed.add_field(
            name="🟢 System",
            value=(
                "Enabled"
                if settings["enabled"]
                else "Disabled"
            ),
            inline=True
        )

        embed.add_field(
            name="🎬 GIF",
            value="Custom GIF configured",
            inline=True
        )

        embed.add_field(
            name="📝 Welcome Message",
            value=settings["welcome_message"][:1000],
            inline=False
        )

        embed.set_thumbnail(
            url=ctx.guild.icon.url
            if ctx.guild.icon
            else self.default_gif
        )

        await ctx.send(
            embed=embed
        )

    # ========================================================
    # TEST WELCOME
    # ========================================================

    @commands.hybrid_command(
        name="testwelcome",
        description="Test the welcome message"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def testwelcome(
        self,
        ctx
    ):

        settings = self.get_settings(
            ctx.guild.id
        )

        member = ctx.author

        message = self.format_message(
            settings["welcome_message"],
            member
        )

        embed = discord.Embed(
            title=(
                f"👑 Welcome to "
                f"{ctx.guild.name}"
            ),
            description=message,
            color=0x8A2BE2
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        if settings["banner_gif"]:

            embed.set_image(
                url=settings["banner_gif"]
            )

        embed.set_footer(
            text=(
                f"{ctx.guild.name} • "
                "Official Community"
            )
        )

        await ctx.send(
            content=f"🎉 Welcome {member.mention}!",
            embed=embed
        )

    # ========================================================
    # TEST GOODBYE
    # ========================================================

    @commands.hybrid_command(
        name="testgoodbye",
        description="Test the goodbye message"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def testgoodbye(
        self,
        ctx
    ):

        settings = self.get_settings(
            ctx.guild.id
        )

        member = ctx.author

        message = self.format_message(
            settings["goodbye_message"],
            member
        )

        embed = discord.Embed(
            title="👋 Goodbye",
            description=message,
            color=0xFF5555
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        if settings["banner_gif"]:

            embed.set_image(
                url=settings["banner_gif"]
            )

        embed.set_footer(
            text=(
                f"{ctx.guild.name} • "
                "HSL & CORPORATION"
            )
        )

        await ctx.send(
            embed=embed
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Welcome(bot)
    )

