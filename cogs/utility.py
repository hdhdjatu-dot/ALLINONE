import discord
from discord import app_commands
from discord.ext import commands


class Utility(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Check the bot latency"
    )
    async def ping(self, interaction: discord.Interaction):

        latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Bot latency: **{latency}ms**",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)


    @app_commands.command(
        name="serverinfo",
        description="Show information about this server"
    )
    async def serverinfo(self, interaction: discord.Interaction):

        guild = interaction.guild

        embed = discord.Embed(
            title=f"📊 {guild.name}",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👑 Owner",
            value=f"<@{guild.owner_id}>",
            inline=True
        )

        embed.add_field(
            name="👥 Members",
            value=str(guild.member_count),
            inline=True
        )

        embed.add_field(
            name="🆔 Server ID",
            value=str(guild.id),
            inline=False
        )

        embed.add_field(
            name="📅 Created",
            value=discord.utils.format_dt(
                guild.created_at,
                style="D"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed)


    @app_commands.command(
        name="userinfo",
        description="Show information about a user"
    )
    @app_commands.describe(
        user="The user you want information about"
    )
    async def userinfo(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None
    ):

        user = user or interaction.user

        embed = discord.Embed(
            title=f"👤 {user.display_name}",
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(
            name="Username",
            value=str(user),
            inline=True
        )

        embed.add_field(
            name="User ID",
            value=str(user.id),
            inline=True
        )

        embed.add_field(
            name="Joined Server",
            value=discord.utils.format_dt(
                user.joined_at,
                style="D"
            ) if user.joined_at else "Unknown",
            inline=False
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))