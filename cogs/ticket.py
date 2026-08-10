
import discord
from discord.ext import commands


# ============================================================
# TICKET BUTTON VIEW
# ============================================================

class TicketPanel(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="hsl_create_ticket"
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        guild = interaction.guild
        user = interaction.user

        # Check existing ticket
        for channel in guild.text_channels:

            if channel.name == f"ticket-{user.id}":

                await interaction.response.send_message(
                    "❌ You already have an open ticket.",
                    ephemeral=True
                )

                return

        # Find / create category
        category = discord.utils.get(
            guild.categories,
            name="🎫 TICKETS"
        )

        if category is None:

            category = await guild.create_category(
                "🎫 TICKETS"
            )

        # Permissions
        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            user:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                ),

            guild.me:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    manage_messages=True
                )
        }

        # Create channel
        channel = await guild.create_text_channel(

            name=f"ticket-{user.id}",

            category=category,

            overwrites=overwrites,

            topic=f"Ticket opened by {user} ({user.id})"
        )

        # Ticket embed
        embed = discord.Embed(

            title="🎫 HSL SUPPORT",

            description=(
                f"Welcome {user.mention}!\n\n"
                "Please describe your issue below.\n"
                "A staff member will assist you shortly."
            ),

            color=discord.Color.blurple()
        )

        embed.add_field(
            name="👤 User",
            value=user.mention,
            inline=True
        )

        embed.add_field(
            name="📅 Opened",
            value=discord.utils.format_dt(
                discord.utils.utcnow(),
                style="F"
            ),
            inline=True
        )

        embed.set_footer(
            text="HSL SECURITY • Support System"
        )

        await channel.send(
            content=user.mention,
            embed=embed,
            view=TicketControls()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )


# ============================================================
# TICKET CONTROL BUTTONS
# ============================================================

class TicketControls(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # --------------------------------------------------------
    # CLOSE
    # --------------------------------------------------------

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.secondary,
        custom_id="hsl_close_ticket"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.channel

        # Disable ticket for everyone
        await channel.set_permissions(
            interaction.guild.default_role,
            view_channel=False
        )

        # Try to identify ticket owner
        topic = channel.topic or ""

        if "Ticket opened by" in topic:

            try:

                user_id = int(
                    topic.split("(")[-1].split(")")[0]
                )

                user = interaction.guild.get_member(
                    user_id
                )

                if user:

                    await channel.set_permissions(
                        user,
                        view_channel=False,
                        send_messages=False
                    )

            except Exception:
                pass

        embed = discord.Embed(

            title="🔒 TICKET CLOSED",

            description=(
                "This ticket has been closed.\n\n"
                "Staff can delete it when finished."
            ),

            color=discord.Color.orange()
        )

        await interaction.response.send_message(
            embed=embed,
            view=ClosedTicketControls()
        )

    # --------------------------------------------------------
    # CLAIM
    # --------------------------------------------------------

    @discord.ui.button(
        label="Claim",
        emoji="🙋",
        style=discord.ButtonStyle.success,
        custom_id="hsl_claim_ticket"
    )
    async def claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        embed = discord.Embed(

            title="🙋 TICKET CLAIMED",

            description=(
                f"This ticket has been claimed by "
                f"{interaction.user.mention}."
            ),

            color=discord.Color.green()
        )

        button.disabled = True

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


# ============================================================
# CLOSED TICKET CONTROLS
# ============================================================

class ClosedTicketControls(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Delete Ticket",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        custom_id="hsl_delete_ticket"
    )
    async def delete_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_message(
            "🗑️ Deleting ticket...",
            ephemeral=True
        )

        await interaction.channel.delete(
            reason=f"Ticket deleted by {interaction.user}"
        )


# ============================================================
# TICKET COG
# ============================================================

class Ticket(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # --------------------------------------------------------
    # TICKET PANEL COMMAND
    # --------------------------------------------------------

    @commands.hybrid_command(
        name="ticketpanel",
        description="Create the support ticket panel"
    )
    @commands.has_permissions(
        administrator=True
    )
    async def ticketpanel(
        self,
        ctx
    ):

        embed = discord.Embed(

            title="🎫 HSL SUPPORT CENTER",

            description=(
                "**Need assistance?**\n\n"
                "Click the button below to create a "
                "private support ticket.\n\n"
                "Our staff will assist you as soon as possible."
            ),

            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📌 Support",
            value="Create a private ticket for assistance.",
            inline=False
        )

        embed.add_field(
            name="🔒 Privacy",
            value="Only you and staff can access your ticket.",
            inline=False
        )

        embed.set_footer(
            text="HSL SECURITY • Support System"
        )

        await ctx.send(
            embed=embed,
            view=TicketPanel()
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        Ticket(bot)
    )

    # Persistent buttons
    bot.add_view(
        TicketPanel()
    )

    bot.add_view(
        TicketControls()
    )

    bot.add_view(
        ClosedTicketControls()
    )
