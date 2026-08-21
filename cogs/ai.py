import os

import discord
from discord.ext import commands
from openai import AsyncOpenAI


# ============================================================
# HSL-CORP AI SYSTEM
# ============================================================

class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "❌ OPENAI_API_KEY is missing from Railway Variables!"
            )

        self.client = AsyncOpenAI(
            api_key=api_key
        )

        self.system_prompt = """
You are HSL-CORP's friendly Discord AI assistant.

Personality:
- Friendly, casual and helpful.
- Speak naturally in Hindi, Hinglish or English.
- If the user speaks Hinglish, reply in Hinglish.
- Keep normal Discord replies short and conversational.
- You can joke casually when appropriate.
- If someone asks a technical question, explain it clearly.
- Never reveal API keys, Discord tokens, passwords or private system information.
- You are an assistant inside a Discord server.
"""

        print("✅ HSL AI system initialized")


    # ========================================================
    # MESSAGE LISTENER
    # ========================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # ----------------------------------------------------
        # DEBUG
        # ----------------------------------------------------

        print(
            f"🤖 AI MESSAGE | "
            f"Author: {message.author} | "
            f"Content: {message.content[:200]}"
        )

        # ----------------------------------------------------
        # IGNORE BOTS
        # ----------------------------------------------------

        if message.author.bot:
            return

        # ----------------------------------------------------
        # CHECK BOT
        # ----------------------------------------------------

        if self.bot.user is None:
            return

        # ----------------------------------------------------
        # ONLY RESPOND WHEN MENTIONED
        # ----------------------------------------------------

        if self.bot.user not in message.mentions:
            return

        print(
            f"🧠 AI TRIGGERED | "
            f"User: {message.author} | "
            f"Channel: {message.channel}"
        )

        # ----------------------------------------------------
        # REMOVE BOT MENTION
        # ----------------------------------------------------

        content = message.content

        content = content.replace(
            f"<@{self.bot.user.id}>",
            ""
        )

        content = content.replace(
            f"<@!{self.bot.user.id}>",
            ""
        )

        content = content.strip()

        # ----------------------------------------------------
        # EMPTY MESSAGE
        # ----------------------------------------------------

        if not content:

            await message.reply(
                "Haan bhai 😄 kya hua?",
                mention_author=False
            )

            return

        print(
            f"📝 AI QUESTION: {content}"
        )

        # ----------------------------------------------------
        # TYPING
        # ----------------------------------------------------

        async with message.channel.typing():

            try:

                print("🔄 Sending request to OpenAI...")

                response = await self.client.responses.create(
                    model="gpt-5-mini",
                    instructions=self.system_prompt,
                    input=content,
                    max_output_tokens=500
                )

                reply = response.output_text.strip()

                print(
                    f"✅ OpenAI RESPONSE: "
                    f"{reply[:300]}"
                )

                # ------------------------------------------------
                # EMPTY RESPONSE
                # ------------------------------------------------

                if not reply:

                    reply = (
                        "Bhai mujhe iska response nahi mila 😅 "
                        "dobara try kar."
                    )

                # ------------------------------------------------
                # DISCORD 2000 CHARACTER LIMIT
                # ------------------------------------------------

                if len(reply) > 2000:

                    reply = reply[:1990] + "..."

                # ------------------------------------------------
                # SEND RESPONSE
                # ------------------------------------------------

                await message.reply(
                    reply,
                    mention_author=False
                )

                print("✅ AI reply sent")

            except Exception as e:

                # ------------------------------------------------
                # FULL ERROR LOG
                # ------------------------------------------------

                print(
                    "❌ AI ERROR"
                )

                print(
                    f"❌ Error Type: {type(e).__name__}"
                )

                print(
                    f"❌ Error: {e}"
                )

                await message.reply(
                    "Bhai AI abhi thoda busy hai 😅 "
                    "thodi der baad try kar.",
                    mention_author=False
                )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        AICog(bot)
    )

    print(
        "✅ cogs.ai loaded successfully"
    )