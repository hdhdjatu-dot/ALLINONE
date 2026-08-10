
import discord
from discord.ext import commands


class Logging(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # Guild ID -> Log Channel ID
        self.log_channels = {}

    # =========================================================
    # GET LOG CHANNEL
    # =========================================================

    def get_log_channel(self, guild):

        channel_id = self.log_channels.get(
            guild.id
        )

        if not channel_id:
            return None

        return guild.get_channel(
            channel_id
        )

    # =========================================================
    # SEND LOG
    # =========================================================

    async def send_log(
        self,
        guild,
        embed
    ):

        channel = self.get_log_channel(
            guild
        )

        if not channel:
            return

        try:

            await channel.send(
                embed=embed
            )

        except Exception as e:

            print(
                f"❌ Logging Error: {e}"
            )

    # =========================================================
    # SET LOG CHANNEL
    # =========================================================

    @commands.hybrid_command(
        name="setlogchannel",
        description="Set the server logging channel"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def setlogchannel(
        self,
        ctx,
        channel: discord.TextChannel = None
    ):

        if channel is None:

            channel = ctx.channel

        self.log_channels[
            ctx.guild.id
        ] = channel.id

        embed = discord.Embed(

            title="🛡️ LOGGING SYSTEM",

            description=(
                f"Logging channel has been set to "
                f"{channel.mention}."
            ),

            color=discord.Color.green()
        )

        embed.set_footer(
            text="HSL SECURITY • Logging System"
        )

        await ctx.send(
            embed=embed
        )

    # =========================================================
    # CLEAR LOG CHANNEL
    # =========================================================

    @commands.hybrid_command(
        name="clearlogchannel",
        description="Disable server logging"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def clearlogchannel(
        self,
        ctx
    ):

        self.log_channels.pop(
            ctx.guild.id,
            None
        )

        embed = discord.Embed(

            title="🛡️ LOGGING SYSTEM",

            description=
                "Logging has been disabled.",

            color=discord.Color.red()
        )

        await ctx.send(
            embed=embed
        )

    # =========================================================
    # MESSAGE DELETE
    # =========================================================

    @commands.Cog.listener()
    async def on_message_delete(
        self,
        message
    ):

        if message.author.bot:
            return

        if not message.guild:
            return

        content = (
            message.content
            if message.content
            else "*No text content*"
        )

        if len(content) > 1000:

            content = content[:1000] + "..."

        embed = discord.Embed(

            title="🗑️ MESSAGE DELETED",

            color=discord.Color.red()
        )

        embed.add_field(

            name="👤 Author",

            value=
                f"{message.author.mention}\n"
                f"`{message.author}`",

            inline=True
        )

        embed.add_field(

            name="📍 Channel",

            value=
                message.channel.mention,

            inline=True
        )

        embed.add_field(

            name="💬 Content",

            value=
                f"```{content}```",

            inline=False
        )

        embed.set_footer(
            text="HSL SECURITY • Message Logs"
        )

        await self.send_log(
            message.guild,
            embed
        )

    # =========================================================
    # MESSAGE EDIT
    # =========================================================

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before,
        after
    ):

        if before.author.bot:
            return

        if not before.guild:
            return

        if before.content == after.content:
            return

        old_content = (
            before.content
            if before.content
            else "*Empty*"
        )

        new_content = (
            after.content
            if after.content
            else "*Empty*"
        )

        old_content = old_content[:800]
        new_content = new_content[:800]

        embed = discord.Embed(

            title="✏️ MESSAGE EDITED",

            color=discord.Color.orange()
        )

        embed.add_field(

            name="👤 Author",

            value=
                f"{before.author.mention}\n"
                f"`{before.author}`",

            inline=True
        )

        embed.add_field(

            name="📍 Channel",

            value=
                before.channel.mention,

            inline=True
        )

        embed.add_field(

            name="🔴 Before",

            value=
                f"```{old_content}```",

            inline=False
        )

        embed.add_field(

            name="🟢 After",

            value=
                f"```{new_content}```",

            inline=False
        )

        embed.set_footer(
            text="HSL SECURITY • Message Logs"
        )

        await self.send_log(
            before.guild,
            embed
        )

    # =========================================================
    # MEMBER JOIN
    # =========================================================

    @commands.Cog.listener()
    async def on_member_join(
        self,
        member
    ):

        embed = discord.Embed(

            title="👤 MEMBER JOINED",

            description=
                f"{member.mention} joined the server.",

            color=discord.Color.green()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(

            name="Username",

            value=
                f"`{member}`",

            inline=True
        )

        embed.add_field(

            name="User ID",

            value=
                f"`{member.id}`",

            inline=True
        )

        embed.add_field(

            name="Members",

            value=
                f"`{member.guild.member_count}`",

            inline=True
        )

        embed.set_footer(
            text="HSL SECURITY • Member Logs"
        )

        await self.send_log(
            member.guild,
            embed
        )

    # =========================================================
    # MEMBER LEAVE
    # =========================================================

    @commands.Cog.listener()
    async def on_member_remove(
        self,
        member
    ):

        embed = discord.Embed(

            title="🚪 MEMBER LEFT",

            description=
                f"**{member}** left the server.",

            color=discord.Color.red()
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(

            name="Username",

            value=
                f"`{member}`",

            inline=True
        )

        embed.add_field(

            name="User ID",

            value=
                f"`{member.id}`",

            inline=True
        )

        embed.add_field(

            name="Members",

            value=
                f"`{member.guild.member_count}`",

            inline=True
        )

        embed.set_footer(
            text="HSL SECURITY • Member Logs"
        )

        await self.send_log(
            member.guild,
            embed
        )

    # =========================================================
    # BAN
    # =========================================================

    @commands.Cog.listener()
    async def on_member_ban(
        self,
        guild,
        user
    ):

        embed = discord.Embed(

            title="🔨 MEMBER BANNED",

            description=
                f"**{user}** was banned.",

            color=discord.Color.dark_red()
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        embed.add_field(

            name="User",

            value=
                f"`{user}`",

            inline=True
        )

        embed.add_field(

            name="User ID",

            value=
                f"`{user.id}`",

            inline=True
        )

        embed.set_footer(
            text="HSL SECURITY • Moderation Logs"
        )

        await self.send_log(
            guild,
            embed
        )

    # =========================================================
    # UNBAN
    # =========================================================

    @commands.Cog.listener()
    async def on_member_unban(
        self,
        guild,
        user
    ):

        embed = discord.Embed(

            title="🔓 MEMBER UNBANNED",

            description=
                f"**{user}** was unbanned.",

            color=discord.Color.green()
        )

        embed.set_thumbnail(
            url=user.display_avatar.url
        )

        embed.add_field(

            name="User",

            value=
                f"`{user}`",

            inline=True
        )

        embed.add_field(

            name="User ID",

            value=
                f"`{user.id}`",

            inline=True
        )

        embed.set_footer(
            text="HSL SECURITY • Moderation Logs"
        )

        await self.send_log(
            guild,
            embed
        )

    # =========================================================
    # ROLE CREATE
    # =========================================================

    @commands.Cog.listener()
    async def on_guild_role_create(
        self,
        role
    ):

        embed = discord.Embed(

            title="🎭 ROLE CREATED",

            description=
                f"New role created: {role.mention}",

            color=discord.Color.green()
        )

        embed.add_field(

            name="Role",

            value=
                f"`{role.name}`",

            inline=True
        )

        embed.add_field(

            name="Role ID",

            value=
                f"`{role.id}`",

            inline=True
        )

        await self.send_log(
            role.guild,
            embed
        )

    # =========================================================
    # ROLE DELETE
    # =========================================================

    @commands.Cog.listener()
    async def on_guild_role_delete(
        self,
        role
    ):

        embed = discord.Embed(

            title="🗑️ ROLE DELETED",

            description=
                f"Role **{role.name}** was deleted.",

            color=discord.Color.red()
        )

        embed.add_field(

            name="Role ID",

            value=
                f"`{role.id}`",

            inline=True
        )

        await self.send_log(
            role.guild,
            embed
        )

    # =========================================================
    # CHANNEL CREATE
    # =========================================================

    @commands.Cog.listener()
    async def on_guild_channel_create(
        self,
        channel
    ):

        embed = discord.Embed(

            title="📁 CHANNEL CREATED",

            description=
                f"Channel created: {channel.mention}",

            color=discord.Color.green()
        )

        embed.add_field(

            name="Channel",

            value=
                f"`{channel.name}`",

            inline=True
        )

        embed.add_field(

            name="Channel ID",

            value=
                f"`{channel.id}`",

            inline=True
        )

        await self.send_log(
            channel.guild,
            embed
        )

    # =========================================================
    # CHANNEL DELETE
    # =========================================================

    @commands.Cog.listener()
    async def on_guild_channel_delete(
        self,
        channel
    ):

        embed = discord.Embed(

            title="🗑️ CHANNEL DELETED",

            description=
                f"Channel **{channel.name}** was deleted.",

            color=discord.Color.red()
        )

        embed.add_field(

            name="Channel ID",

            value=
                f"`{channel.id}`",

            inline=True
        )

        await self.send_log(
            channel.guild,
            embed
        )


# =============================================================
# SETUP
# =============================================================

async def setup(bot):

    await bot.add_cog(
        Logging(bot)
    )

