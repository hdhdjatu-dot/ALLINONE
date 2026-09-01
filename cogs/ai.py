import os
import json
import time
import asyncio

import discord
from discord.ext import commands
from discord import app_commands

from google import genai
from google.genai import types


# ============================================================
# HSL-CORP GEMINI AI SYSTEM
# ============================================================

DATA_FILE = "ai_data.json"

MAX_MEMORY_MESSAGES = 12
USER_COOLDOWN = 15

# ============================================================
# GEMINI MODELS
# First = preferred
# Others = fallback if temporary 503/overload happens
# ============================================================

GEMINI_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
]


class AICog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        # ========================================================
        # GEMINI API
        # ========================================================

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:

            raise RuntimeError(
                "❌ GEMINI_API_KEY is missing from Railway Variables!"
            )

        self.client = genai.Client(
            api_key=api_key
        )

        # ========================================================
        # DATA
        # ========================================================

        self.data_lock = asyncio.Lock()

        self.data = {
            "enabled": True,
            "ai_channels": {},
            "memory": {}
        }

        self.load_data()

        # ========================================================
        # COOLDOWN
        # ========================================================

        self.cooldowns = {}

        # ========================================================
        # AI PERSONALITY
        # ========================================================

        self.system_prompt = """
You are AFF-ARMY official Discord AI assistant.

PERSONALITY:
- Friendly, natural and casual.
- Speak like a real Discord friend.
- Hindi, Hinglish and English are supported.
- If the user speaks Hinglish, reply in Hinglish.
- If the user speaks English, reply in English.
- Keep normal Discord conversations reasonably short.
- You can use emojis naturally.
- Be helpful with coding, Discord bots, gaming and general questions.
- Do not unnecessarily repeat the user's question.
- Do not reveal API keys, Discord tokens, passwords or private
  system information.
- Never claim you performed an action that you did not perform.
- Be respectful.

You are part of AFF-ARMY's Discord server.
"""

        print(
            "==========================================",
            flush=True
        )

        print(
            "✅ AFF AI SYSTEM INITIALIZED",
            flush=True
        )

        print(
            f"🧠 Preferred model: {GEMINI_MODELS[0]}",
            flush=True
        )

        print(
            f"🔄 Fallback models: {', '.join(GEMINI_MODELS[1:])}",
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )


    # ============================================================
    # LOAD DATA
    # ============================================================

    def load_data(self):

        try:

            if os.path.exists(DATA_FILE):

                with open(
                    DATA_FILE,
                    "r",
                    encoding="utf-8"
                ) as f:

                    loaded = json.load(f)

                if isinstance(loaded, dict):

                    self.data.update(
                        loaded
                    )

                print(
                    "💾 AI data loaded",
                    flush=True
                )

            else:

                self.save_data_sync()

                print(
                    "💾 New AI data file created",
                    flush=True
                )

        except Exception as e:

            print(
                f"❌ AI data load error: {e}",
                flush=True
            )


    # ============================================================
    # SAVE DATA
    # ============================================================

    def save_data_sync(self):

        try:

            with open(
                DATA_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.data,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

        except Exception as e:

            print(
                f"❌ AI data save error: {e}",
                flush=True
            )


    async def save_data(self):

        async with self.data_lock:

            await asyncio.to_thread(
                self.save_data_sync
            )


    # ============================================================
    # MEMORY KEY
    # ============================================================

    def get_memory_key(
        self,
        guild_id,
        user_id
    ):

        return f"{guild_id}:{user_id}"


    # ============================================================
    # GET USER MEMORY
    # ============================================================

    def get_memory(
        self,
        guild_id,
        user_id
    ):

        key = self.get_memory_key(
            guild_id,
            user_id
        )

        memory = self.data.setdefault(
            "memory",
            {}
        )

        return memory.setdefault(
            key,
            []
        )


    # ============================================================
    # ADD MEMORY
    # ============================================================

    def add_memory(
        self,
        guild_id,
        user_id,
        role,
        content
    ):

        memory = self.get_memory(
            guild_id,
            user_id
        )

        memory.append(
            {
                "role": role,
                "content": content
            }
        )

        if len(memory) > MAX_MEMORY_MESSAGES:

            del memory[
                :-MAX_MEMORY_MESSAGES
            ]


    # ============================================================
    # BUILD PROMPT
    # ============================================================

    def build_input(
        self,
        guild_id,
        user_id,
        current_message
    ):

        memory = self.get_memory(
            guild_id,
            user_id
        )

        conversation = []

        for item in memory:

            role = item.get(
                "role",
                "user"
            )

            content = item.get(
                "content",
                ""
            )

            if not content:
                continue

            if role == "user":

                conversation.append(
                    f"User: {content}"
                )

            else:

                conversation.append(
                    f"Assistant: {content}"
                )

        conversation.append(
            f"User: {current_message}"
        )

        return "\n".join(
            conversation
        )


    # ============================================================
    # COOLDOWN
    # ============================================================

    def is_on_cooldown(
        self,
        user_id
    ):

        now = time.time()

        last_time = self.cooldowns.get(
            user_id,
            0
        )

        remaining = USER_COOLDOWN - (
            now - last_time
        )

        if remaining > 0:

            return True, remaining

        self.cooldowns[
            user_id
        ] = now

        return False, 0


    # ============================================================
    # GEMINI REQUEST
    # ============================================================

    async def generate_response(
        self,
        guild_id,
        user_id,
        content
    ):

        prompt = self.build_input(
            guild_id,
            user_id,
            content
        )

        last_error = None

        # ========================================================
        # TRY EACH MODEL
        # ========================================================

        for model_index, model in enumerate(
            GEMINI_MODELS
        ):

            for attempt in range(1, 3):

                try:

                    print(
                        f"🔄 Gemini request | "
                        f"Model={model} | "
                        f"Attempt={attempt}",
                        flush=True
                    )

                    response = await self.client.aio.models.generate_content(

                        model=model,

                        contents=prompt,

                        config=types.GenerateContentConfig(
                            system_instruction=self.system_prompt,
                            max_output_tokens=500
                        )
                    )

                    reply = response.text

                    if reply:

                        reply = reply.strip()

                    if not reply:

                        print(
                            f"⚠️ Empty response from {model}",
                            flush=True
                        )

                        continue

                    print(
                        f"✅ Gemini success | Model={model}",
                        flush=True
                    )

                    return reply

                except Exception as e:

                    last_error = e

                    error_text = str(e)

                    print(
                        "------------------------------------------",
                        flush=True
                    )

                    print(
                        f"❌ Gemini model failed: {model}",
                        flush=True
                    )

                    print(
                        f"❌ Attempt: {attempt}",
                        flush=True
                    )

                    print(
                        f"❌ Type: {type(e).__name__}",
                        flush=True
                    )

                    print(
                        f"❌ Error: {error_text}",
                        flush=True
                    )

                    print(
                        "------------------------------------------",
                        flush=True
                    )

                    # =================================================
                    # Retry temporary errors
                    # =================================================

                    temporary_error = any(
                        x in error_text.lower()
                        for x in [
                            "503",
                            "unavailable",
                            "high demand",
                            "429",
                            "resource exhausted",
                            "temporarily"
                        ]
                    )

                    if temporary_error:

                        if attempt == 1:

                            print(
                                "⏳ Temporary Gemini error. "
                                "Retrying in 2 seconds...",
                                flush=True
                            )

                            await asyncio.sleep(
                                2
                            )

                        continue

                    # Non-temporary error
                    break

            # =====================================================
            # Move to fallback model
            # =====================================================

            if model_index < len(
                GEMINI_MODELS
            ) - 1:

                print(
                    f"🔄 Switching fallback model "
                    f"→ {GEMINI_MODELS[model_index + 1]}",
                    flush=True
                )

                await asyncio.sleep(
                    1
                )

        # ========================================================
        # EVERYTHING FAILED
        # ========================================================

        if last_error:

            raise last_error

        return None


    # ============================================================
    # PROCESS AI MESSAGE
    # ============================================================

    async def process_ai_message(
        self,
        message,
        content
    ):

        if not message.guild:

            return

        guild_id = str(
            message.guild.id
        )

        user_id = str(
            message.author.id
        )

        # ========================================================
        # COOLDOWN
        # ========================================================

        on_cooldown, remaining = self.is_on_cooldown(
            user_id
        )

        if on_cooldown:

            print(
                f"⏳ AI cooldown | "
                f"User={message.author} | "
                f"Remaining={remaining:.1f}s",
                flush=True
            )

            return

        # ========================================================
        # EMPTY MESSAGE
        # ========================================================

        if not content.strip():

            await message.reply(
                "Haan bhai 😄 kya hua?",
                mention_author=False
            )

            return

        print(
            f"🧠 AI QUESTION: {content}",
            flush=True
        )

        try:

            async with message.channel.typing():

                print(
                    "🔄 Sending request to Gemini...",
                    flush=True
                )

                reply = await self.generate_response(
                    guild_id,
                    user_id,
                    content
                )

                if not reply:

                    await message.reply(
                        "Bhai Gemini ne response nahi diya 😅",
                        mention_author=False
                    )

                    return

                # =================================================
                # SAVE MEMORY
                # =================================================

                self.add_memory(
                    guild_id,
                    user_id,
                    "user",
                    content
                )

                self.add_memory(
                    guild_id,
                    user_id,
                    "assistant",
                    reply
                )

                await self.save_data()

                # =================================================
                # DISCORD LIMIT
                # =================================================

                if len(reply) > 2000:

                    reply = reply[:1990] + "..."

                # =================================================
                # SEND
                # =================================================

                await message.reply(
                    reply,
                    mention_author=False
                )

                print(
                    "✅ Gemini reply sent successfully",
                    flush=True
                )

        except Exception as e:

            print(
                "==========================================",
                flush=True
            )

            print(
                "❌ GEMINI AI FINAL ERROR",
                flush=True
            )

            print(
                f"❌ Error Type: {type(e).__name__}",
                flush=True
            )

            print(
                f"❌ Error: {e}",
                flush=True
            )

            print(
                "==========================================",
                flush=True
            )

            try:

                await message.reply(
                    "Bhai AI abhi thoda busy hai 😅 "
                    "thodi der baad try kar.",
                    mention_author=False
                )

            except Exception as discord_error:

                print(
                    f"❌ Discord reply error: "
                    f"{discord_error}",
                    flush=True
                )


    # ============================================================
    # MESSAGE LISTENER
    # ============================================================

    @commands.Cog.listener()
    async def on_message(
        self,
        message: discord.Message
    ):

        print(
            f"🤖 AI MESSAGE RECEIVED | "
            f"Author={message.author} | "
            f"Bot={message.author.bot} | "
            f"Content={message.content[:200]}",
            flush=True
        )

        # ========================================================
        # IGNORE BOTS
        # ========================================================

        if message.author.bot:

            return

        # ========================================================
        # SERVER ONLY
        # ========================================================

        if not message.guild:

            return

        # ========================================================
        # GLOBAL AI STATUS
        # ========================================================

        if not self.data.get(
            "enabled",
            True
        ):

            return

        # ========================================================
        # IGNORE PREFIX COMMANDS
        # ========================================================

        if message.content.startswith("!"):

            return

        # ========================================================
        # CHECK MENTION
        # ========================================================

        mentioned = False

        if self.bot.user:

            mentioned = (
                self.bot.user
                in message.mentions
            )

        # ========================================================
        # CHECK AI CHANNEL
        # ========================================================

        ai_channel_id = self.data.get(
            "ai_channels",
            {}
        ).get(
            str(message.guild.id)
        )

        is_ai_channel = (
            ai_channel_id is not None
            and str(message.channel.id)
            == str(ai_channel_id)
        )

        # ========================================================
        # ONLY AI CHANNEL OR MENTION
        # ========================================================

        if not mentioned and not is_ai_channel:

            return

        print(
            f"🧠 AI TRIGGERED | "
            f"Mention={mentioned} | "
            f"AIChannel={is_ai_channel}",
            flush=True
        )

        # ========================================================
        # REMOVE BOT MENTION
        # ========================================================

        content = message.content

        if self.bot.user:

            content = content.replace(
                f"<@{self.bot.user.id}>",
                ""
            )

            content = content.replace(
                f"<@!{self.bot.user.id}>",
                ""
            )

        content = content.strip()

        await self.process_ai_message(
            message,
            content
        )


    # ============================================================
    # /AICHANNEL
    # ============================================================

    @app_commands.command(
        name="aichannel",
        description="Set or disable the AI chat channel."
    )
    @app_commands.describe(
        channel="Channel where AI should automatically chat."
    )
    @app_commands.default_permissions(
        manage_guild=True
    )
    async def aichannel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None
    ):

        if not interaction.guild:

            await interaction.response.send_message(
                "❌ This command can only be used in a server.",
                ephemeral=True
            )

            return

        if not interaction.user.guild_permissions.manage_guild:

            await interaction.response.send_message(
                "❌ You need **Manage Server** permission.",
                ephemeral=True
            )

            return

        guild_id = str(
            interaction.guild.id
        )

        # ========================================================
        # DISABLE
        # ========================================================

        if channel is None:

            self.data.setdefault(
                "ai_channels",
                {}
            ).pop(
                guild_id,
                None
            )

            await self.save_data()

            await interaction.response.send_message(
                "🔴 **AI channel disabled.**\n"
                "AI will now only reply when mentioned.",
                ephemeral=True
            )

            print(
                f"🔴 AI channel disabled | "
                f"Guild={interaction.guild.id}",
                flush=True
            )

            return

        # ========================================================
        # SET
        # ========================================================

        self.data.setdefault(
            "ai_channels",
            {}
        )[guild_id] = str(
            channel.id
        )

        await self.save_data()

        await interaction.response.send_message(
            f"🟢 **AI channel set!**\n\n"
            f"💬 Channel: {channel.mention}\n\n"
            f"AI will automatically reply in this channel.",
            ephemeral=True
        )

        print(
            f"🟢 AI channel set | "
            f"Guild={interaction.guild.id} | "
            f"Channel={channel.id}",
            flush=True
        )


    # ============================================================
    # /AION
    # ============================================================

    @app_commands.command(
        name="aion",
        description="Enable AFF AI."
    )
    @app_commands.default_permissions(
        manage_guild=True
    )
    async def aion(
        self,
        interaction: discord.Interaction
    ):

        if not interaction.guild:

            await interaction.response.send_message(
                "❌ Server only.",
                ephemeral=True
            )

            return

        if not interaction.user.guild_permissions.manage_guild:

            await interaction.response.send_message(
                "❌ You need **Manage Server** permission.",
                ephemeral=True
            )

            return

        self.data[
            "enabled"
        ] = True

        await self.save_data()

        await interaction.response.send_message(
            "🟢 **AFF AI enabled!**",
            ephemeral=True
        )


    # ============================================================
    # /AIOFF
    # ============================================================

    @app_commands.command(
        name="aioff",
        description="Disable AFF AI."
    )
    @app_commands.default_permissions(
        manage_guild=True
    )
    async def aioff(
        self,
        interaction: discord.Interaction
    ):

        if not interaction.guild:

            await interaction.response.send_message(
                "❌ Server only.",
                ephemeral=True
            )

            return

        if not interaction.user.guild_permissions.manage_guild:

            await interaction.response.send_message(
                "❌ You need **Manage Server** permission.",
                ephemeral=True
            )

            return

        self.data[
            "enabled"
        ] = False

        await self.save_data()

        await interaction.response.send_message(
            "🔴 **AFF AI disabled!**",
            ephemeral=True
        )


    # ============================================================
    # /AISTATUS
    # ============================================================

    @app_commands.command(
        name="aistatus",
        description="Show AFF AI status."
    )
    async def aistatus(
        self,
        interaction: discord.Interaction
    ):

        enabled = self.data.get(
            "enabled",
            True
        )

        status = (
            "🟢 Enabled"
            if enabled
            else
            "🔴 Disabled"
        )

        channel_text = "Not set"

        if interaction.guild:

            channel_id = self.data.get(
                "ai_channels",
                {}
            ).get(
                str(interaction.guild.id)
            )

            if channel_id:

                channel = interaction.guild.get_channel(
                    int(channel_id)
                )

                if channel:

                    channel_text = channel.mention

                else:

                    channel_text = f"<#{channel_id}>"

        embed = discord.Embed(
            title="🤖 AFF-ARMY AI STATUS",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="AI",
            value=status,
            inline=True
        )

        embed.add_field(
            name="AI Channel",
            value=channel_text,
            inline=True
        )

        embed.add_field(
            name="Memory",
            value="🧠 Enabled",
            inline=True
        )

        embed.add_field(
            name="Model",
            value=GEMINI_MODELS[0],
            inline=False
        )

        embed.set_footer(
            text="AFF ARMY • AI SYSTEM"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


    # ============================================================
    # /AICLEARMEMORY
    # ============================================================

    @app_commands.command(
        name="aiclearmemory",
        description="Clear your AFF AI conversation memory."
    )
    async def aiclearmemory(
        self,
        interaction: discord.Interaction
    ):

        if not interaction.guild:

            await interaction.response.send_message(
                "❌ Server only.",
                ephemeral=True
            )

            return

        key = self.get_memory_key(
            interaction.guild.id,
            interaction.user.id
        )

        self.data.setdefault(
            "memory",
            {}
        ).pop(
            key,
            None
        )

        await self.save_data()

        await interaction.response.send_message(
            "🧹 **Your AI memory has been cleared.**",
            ephemeral=True
        )

        print(
            f"🧹 AI memory cleared | "
            f"User={interaction.user} | "
            f"Guild={interaction.guild.id}",
            flush=True
        )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        AICog(bot)
    )

    print(
        "✅ cogs.ai loaded successfully",
        flush=True
    )