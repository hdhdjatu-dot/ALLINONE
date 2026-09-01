print("🔥🔥🔥 HSL MAIN.PY LOADED - AI VERSION 🔥🔥🔥", flush=True)
import os
import discord
from discord.ext import commands
from config import TOKEN
from cogs.database import Database
import aiohttp
from dotenv import load_dotenv

load_dotenv()
# Load Opus for audio playback
if not discord.opus.is_loaded():
    try:
        discord.opus.load_opus('libopus.so.0')
    except Exception:
        try:
            discord.opus.load_opus('libopus.so')
        except Exception:
            pass

TOKEN = os.getenv("TOKEN") or TOKEN

class HSLBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.all()
        
        super().__init__(
            command_prefix="!",
            intents=intents            
        )
        self.db = Database()
        print("✅ database.py loaded")
              
    async def setup_hook(self):
        
        print("🚀 HSL SETUP_HOOK STARTED", flush=True)
        print("🔄 Loading utility.py...")
        await self.load_extension("cogs.utility")
        print("✅ utility.py loaded")

        print("🔄 Loading security.py...")
        await self.load_extension("cogs.security")
        print("✅ security.py loaded")
        
        print("🔄 Loading warnings.py...")
        await self.load_extension("cogs.warnings")
        print("✅ warnings.py loaded")
        
        print("🔄 Loading automod.py...")
        await self.load_extension("cogs.automod")
        print("✅ automod.py loaded")
        
        print("🔄 Loading logging.py...")
        await self.load_extension("cogs.logging")
        print("✅ logging.py loaded")
        
        print("🔄 Loading music.py...")
        await self.load_extension("cogs.music")
        print("✅ music.py loaded")
        
        print("🔄 Loading ticket.py...")
        await self.load_extension("cogs.ticket")
        print("✅ ticket.py loaded")
        
        print("🔄 Loading welcome.py...")
        await self.load_extension("cogs.welcome")
        print("✅ welcome.py loaded")
     
        print("🔄 Loading infoCommands.py...")
        await self.load_extension("cogs.infoCommands")
        print("✅ infoCommands.py loaded")

        print("🔄 Loading ai.py...", flush=True)
        await self.load_extension("cogs.ai")
        print("✅ ai.py loaded", flush=True)

        print("🔄 Loading tts.py...", flush=True)
        await self.load_extension("cogs.tts")
        print("✅ tts.py loaded", flush=True)
           
        guild_ids = [
            1435943252455981080,  # Server 1
            
               
        ]

        for guild_id in guild_ids:
            guild = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"✅ Synced {len(synced)} commands to server {guild_id}")


# ============================================================
# CUSTOM HSL HELP COMMAND
# ============================================================

class HSLHelp(commands.HelpCommand):

    async def send_bot_help(self, mapping):

        ctx = self.context

        embed = discord.Embed(
            title="👑 HSL & CORPORATION",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🛡️ **HSL SECURITY BOT**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Use `!help <command>` for detailed information.\n"
                "Use `!help <category>` to view category commands."
            ),
            color=discord.Color.blurple()
        )

        category_emojis = {
            "Music": "🎵",
            "Ticket": "🎫",
            "Welcome": "👋",
            "Logging": "📋",
            "Security": "🛡️",
            "Warnings": "⚠️",
            "Automod": "🤖",
            "Utility": "🔧",
        }

        for cog, commands_list in mapping.items():

            if cog is None:
                continue

            commands_list = [
                command
                for command in commands_list
                if not command.hidden
            ]

            if not commands_list:
                continue

            name = cog.qualified_name

            emoji = category_emojis.get(
                name,
                "📁"
            )

            command_text = ""

            for command in commands_list:

                command_text += (
                    f"`!{command.name}`  "
                    f"— {command.description or 'No description'}\n"
                )

            embed.add_field(
                name=f"{emoji} {name}",
                value=command_text,
                inline=False
            )

        embed.add_field(
            name="💡 Quick Help",
            value=(
                "`!help music`\n"
                "`!help ticket`\n"
                "`!help welcome`\n"
                "`!help logging`"
            ),
            inline=False
        )

        embed.set_footer(
            text="HSL & CORPORATION • Command Center"
        )

        await ctx.send(
            embed=embed
        )

    async def send_command_help(self, command):

        embed = discord.Embed(
            title=f"📖 !{command.name}",
            description=(
                command.description
                or "No description available."
            ),
            color=discord.Color.blurple()
        )

        if command.aliases:

            embed.add_field(
                name="🔗 Aliases",
                value=" ".join(
                    f"`!{alias}`"
                    for alias in command.aliases
                ),
                inline=False
            )

        embed.set_footer(
            text="HSL & CORPORATION • Command Help"
        )

        await self.context.send(
            embed=embed
        )

    async def send_cog_help(self, cog):

        embed = discord.Embed(
            title=f"📂 {cog.qualified_name}",
            description=(
                f"Commands available in "
                f"**{cog.qualified_name}**"
            ),
            color=discord.Color.blurple()
        )

        for command in cog.get_commands():

            if command.hidden:
                continue

            embed.add_field(
                name=f"!{command.name}",
                value=(
                    command.description
                    or "No description"
                ),
                inline=False
            )

        embed.set_footer(
            text="HSL & CORPORATION • Command Center"
        )

        await self.context.send(
            embed=embed
        )


# ============================================================
# BOT INSTANCE & EVENTS
# ============================================================

bot = HSLBot()

# Replace Discord's default help command
bot.help_command = HSLHelp()


@bot.event
async def on_ready():

    print("=" * 45)
    print(f"🤖 Bot: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌐 Servers: {len(bot.guilds)}")
    print("=" * 45)


if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN missing in environment or config!")

bot.run(TOKEN)