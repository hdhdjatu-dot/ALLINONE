import os

import discord
from discord.ext import commands
from google import genai
from google.genai import types


# ============================================================
# HSL-CORP GEMINI AI SYSTEM
# ============================================================

class AICog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # --------------------------------------------------------
        # GEMINI API KEY
        # --------------------------------------------------------

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "❌ GEMINI_API_KEY is missing from Railway Variables!"
            )

        self.client = genai.Client(
            api_key=api_key
        )

        # --------------------------------------------------------
        # AI PERSONALITY
        # --------------------------------------------------------

        self.system_prompt = """
You are HSL-CORP's friendly Discord AI assistant.

Personality:
- Friendly, casual and helpful.
- Speak naturally in Hindi, Hinglish or English.
- If the user speaks Hinglish, reply in Hinglish.
- Keep normal Discord replies short and conversational.
- You can joke casually when appropriate.
- If someone asks a technical question, explain it clearly.
- Never reveal API keys, Discord tokens, passwords or private
  system information.
- You are an assistant inside a Discord server.
"""

        print(
            "✅ HSL Gemini AI system initialized",
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

        # --------------------------------------------------------
        # DEBUG
        # --------------------------------------------------------

        print(
            f"🤖 AI MESSAGE RECEIVED | "
            f"Author={message.author} | "
            f"Bot={message.author.bot} | "
            f"Content={message.content[:300]}",
            flush=True
        )

        # --------------------------------------------------------
        # IGNORE BOTS
        # --------------------------------------------------------

        if message.author.bot:
            return

        # --------------------------------------------------------
        # CHECK BOT USER
        # --------------------------------------------------------

        if self.bot.user is None:
            return

        # --------------------------------------------------------
        # ONLY RESPOND WHEN MENTIONED
        # --------------------------------------------------------

        if self.bot.user not in message.mentions:

            print(
                "ℹ️ AI: bot was not mentioned",
                flush=True
            )

            return

        print(
            f"🧠 GEMINI TRIGGERED | "
            f"User={message.author} | "
            f"Channel={message.channel}",
            flush=True
        )

        # --------------------------------------------------------
        # REMOVE BOT MENTION
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # EMPTY MESSAGE
        # --------------------------------------------------------

        if not content:

            await message.reply(
                "Haan bhai 😄 kya hua?",
                mention_author=False
            )

            return

        print(
            f"📝 GEMINI QUESTION: {content}",
            flush=True
        )

        # --------------------------------------------------------
        # TYPING
        # --------------------------------------------------------

        try:

            async with message.channel.typing():

                print(
                    "🔄 Sending request to Gemini...",
                    flush=True
                )

                # ------------------------------------------------
                # GEMINI REQUEST
                # ------------------------------------------------

                response = await self.client.aio.models.generate_content(

                    model="gemini-3.7-flash",

                    contents=content,

                    config=types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        max_output_tokens=500,
                        temperature=0.8
                    )
                )

                # ------------------------------------------------
                # RESPONSE TEXT
                # ------------------------------------------------

                reply = response.text

                if reply:
                    reply = reply.strip()

                print(
                    f"✅ GEMINI RESPONSE: {reply[:500] if reply else 'EMPTY'}",
                    flush=True
                )

                # ------------------------------------------------
                # EMPTY RESPONSE
                # ------------------------------------------------

                if not reply:

                    reply = (
                        "Bhai Gemini ne response nahi diya 😅 "
                        "dobara try kar."
                    )

                # ------------------------------------------------
                # DISCORD 2000 CHARACTER LIMIT
                # ------------------------------------------------

                if len(reply) > 2000:

                    reply = reply[:1990] + "..."

                # ------------------------------------------------
                # SEND
                # ------------------------------------------------

                await message.reply(
                    reply,
                    mention_author=False
                )

                print(
                    "✅ Gemini reply sent successfully",
                    flush=True
                )

        # --------------------------------------------------------
        # ERROR
        # --------------------------------------------------------

        except Exception as e:

            print(
                "==========================================",
                flush=True
            )

            print(
                "❌ GEMINI AI ERROR",
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
                    f"❌ Discord reply error: {discord_error}",
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
        "✅ cogs.ai Gemini loaded successfully",
        flush=True
    )