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

        # Memory history
        self.message_history = defaultdict(lambda: deque(maxlen=20))
        self.last_messages = {}
        self.duplicate_counts = defaultdict(int)

        # Module Settings
        self.settings = defaultdict(
            lambda: {
                "links": True,
                "spam": True,
                "duplicates": True,
                "badwords": True
            }
        )

        # Regex Patterns
        self.link_pattern = re.compile(
            r"(https?://\S+|www\.\S+|discord\.gg/\S+|discord\.com/invite/\S+)",
            re.IGNORECASE
        )

        # Badwords List
        self.bad_words = {
            "mc", "randi", "maderchod", "chakka", "bhenchod",
            "bhosdika", "chutiye", "bsdk", "gand", "gand mara",
            "muh me lele", "teri maa chod dunga", "tun chakka hai",
            "bc", "bhosdike", "chutiya", "lodu", "bkl" ,"bhen ka loda" "maa ka bhosda" ,"chut"  ,"bhund", "fudda" ,"sex" ,"radn" ,"randdd"





        }

        # Limits
        self.max_messages = 5
        self.time_window = 5
        self.max_duplicates = 3
        self.automod_timeout_minutes = 10

    def is_server_owner(self, message):
        return message.guild is not None and message.guild.owner_id == message.author.id

    async def timeout_member(self, member, reason):
        try:
            await member.timeout(
                timedelta(minutes=self.automod_timeout_minutes),
                reason=reason
            )
            return True
        except discord.Forbidden:
            print(f"[AUTOMOD] Cannot timeout {member} - Missing permissions or role hierarchy issue.")
            return False
        except Exception as e:
            print(f"[AUTOMOD] Timeout error: {e}")
            return False

    def security_embed(self, title, description, color):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        embed.set_footer(text="HSL SECURITY • AutoMod Protection")
        return embed

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                row = self.bot.db.get_guild(guild.id) if hasattr(self.bot, 'db') else None
                if row:
                    self.settings[guild.id]["links"] = bool(row.get("automod_links", True))
                    self.settings[guild.id]["spam"] = bool(row.get("automod_spam", True))
                    self.settings[guild.id]["duplicates"] = bool(row.get("automod_duplicates", True))
                    self.settings[guild.id]["badwords"] = bool(row.get("automod_badwords", True))
            except Exception as e:
                print(f"[AUTOMOD] Database load error: {e}")

        print("💾 AutoMod settings loaded")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        # Owner bypass
        if self.is_server_owner(message):
            return

        # NOTE: Manage Messages walla bypass comment-out kiya hai
        # Agar admin/mod ko ignore karna ho toh isline ko uncomment kar dena:
        # if message.author.guild_permissions.manage_messages: return

        settings = self.settings[message.guild.id]

        # ----------------------------------------------------
        # ANTI-LINK
        # ----------------------------------------------------
        if settings["links"] and self.link_pattern.search(message.content):
            try:
                await message.delete()
            except Exception:
                pass

            timed_out = await self.timeout_member(message.author, "HSL AutoMod: Unauthorized link")

            if timed_out:
                embed = self.security_embed(
                    "🔗 LINK BLOCKED",
                    f"### 🛡️ Security Action\n\n👤 **Member:** {message.author.mention}\n\n🔗 **Violation:** Unauthorized link\n\n🟢 **Action:** 10 Minute Timeout\n\n🗑️ **Message:** Deleted",
                    discord.Color.red()
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                await message.channel.send(embed=embed, delete_after=7)
            return

        # ----------------------------------------------------
        # ANTI-BADWORD
        # ----------------------------------------------------
        if settings["badwords"]:
            content = message.content.lower()
            found = False

            for word in self.bad_words:
                pattern = r'\b' + re.escape(word) + r'\b'
                if re.search(pattern, content):
                    found = True
                    break

            if found:
                try:
                    await message.delete()
                except Exception:
                    pass

                timed_out = await self.timeout_member(message.author, "HSL AutoMod: Inappropriate language")

                if timed_out:
                    embed = self.security_embed(
                        "🚨 LANGUAGE VIOLATION",
                        f"### 🛡️ Security Action\n\n👤 **Member:** {message.author.mention}\n\n⚠️ **Violation:** Inappropriate language\n\n🟢 **Action:** 10 Minute Timeout\n\n🗑️ **Message:** Deleted",
                        discord.Color.red()
                    )
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    await message.channel.send(embed=embed, delete_after=7)
                else:
                    await message.channel.send(
                        f"⚠️ **AutoMod Alert:** {message.author.mention} ne bad word use kiya, lekin bot ke paas **Timeout** dene ki permission / role priority nahi hai!",
                        delete_after=7
                    )
                return

        # ----------------------------------------------------
        # ANTI-SPAM
        # ----------------------------------------------------
        if settings["spam"]:
            user_id = message.author.id
            now = time.monotonic()
            history = self.message_history[user_id]
            history.append(now)

            while history and now - history[0] > self.time_window:
                history.popleft()

            if len(history) >= self.max_messages:
                try:
                    await message.delete()
                except Exception:
                    pass

                timed_out = await self.timeout_member(message.author, "HSL AutoMod: Spamming")

                if timed_out:
                    embed = self.security_embed(
                        "🚨 SPAM DETECTED",
                        f"### 🛡️ Security Action\n\n👤 **Member:** {message.author.mention}\n\n📊 **Violation:** Message spam\n\n🟢 **Action:** 10 Minute Timeout",
                        discord.Color.red()
                    )
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    await message.channel.send(embed=embed, delete_after=7)

                history.clear()
                return

        # ----------------------------------------------------
        # ANTI-DUPLICATE
        # ----------------------------------------------------
        if settings["duplicates"]:
            user_id = message.author.id
            content = message.content.strip().lower()

            if content and self.last_messages.get(user_id) == content:
                self.duplicate_counts[user_id] += 1

                if self.duplicate_counts[user_id] >= self.max_duplicates:
                    try:
                        await message.delete()
                    except Exception:
                        pass

                    timed_out = await self.timeout_member(message.author, "HSL AutoMod: Repeated messages")

                    if timed_out:
                        embed = self.security_embed(
                            "🔁 REPEATED MESSAGE",
                            f"### 🛡️ Security Action\n\n👤 **Member:** {message.author.mention}\n\n⚠️ **Violation:** Repeated message\n\n🟢 **Action:** 10 Minute Timeout",
                            discord.Color.red()
                        )
                        embed.set_thumbnail(url=message.author.display_avatar.url)
                        await message.channel.send(embed=embed, delete_after=7)

                    self.duplicate_counts[user_id] = 0
                    return
            else:
                self.duplicate_counts[user_id] = 0

            self.last_messages[user_id] = content

    @app_commands.command(name="automod_status", description="Show AutoMod security status")
    @app_commands.checks.has_permissions(administrator=True)
    async def automod_status(self, interaction: discord.Interaction):
        settings = self.settings[interaction.guild.id]

        def status(value):
            return "🟢 **ONLINE**" if value else "🔴 **OFFLINE**"

        embed = discord.Embed(
            title="🛡️ HSL SECURITY",
            description="### SECURITY STATUS\n\n━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.green()
        )
        embed.add_field(name="🔗 Anti-Link", value=status(settings["links"]), inline=True)
        embed.add_field(name="🚨 Anti-Spam", value=status(settings["spam"]), inline=True)
        embed.add_field(name="🔁 Anti-Duplicate", value=status(settings["duplicates"]), inline=True)
        embed.add_field(name="🤬 Anti-Badword", value=status(settings["badwords"]), inline=True)
        embed.add_field(name="🔇 Auto Timeout", value="🟢 **10 MINUTES**", inline=True)
        embed.set_footer(text="HSL SECURITY • Protection System")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AutoMod(bot))