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

        # --------------------------------------------------------
        # OPENAI API KEY
        # --------------------------------------------------------

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "❌ OPENAI_API_KEY is missing from Railway Variables!"
            )

        self.client = AsyncOpenAI(
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
            "✅ HSL AI system initialized",
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
        # DEBUG - EVERY MESSAGE
        # --------------------------------------------------------

        print(
            f"🤖 AI MESSAGE RECEIVED | "
            f"Author={message.author} | "
            f"Bot={message.author.bot} | "
            f"Content={message.content[:300]}",
            flush=True
        )

        # --------------------------------------------------------
        # IGNORE BOT MESSAGES
        # --------------------------------------------------------

        if message.author.bot:
            return

        # --------------------------------------------------------
        # CHECK BOT USER
        # --------------------------------------------------------

        if self.bot.user is None:

            print(
                "⚠️ AI: bot.user is None",
                flush=True
            )

            return

        # --------------------------------------------------------
        # CHECK MENTION
        # --------------------------------------------------------

        if self.bot.user not in message.mentions:

            print(
                "ℹ️ AI: message does not mention bot",
                flush=True
            )

            return

        print(
            f"🧠 AI TRIGGERED | "
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

            print(
                "ℹ️ AI: empty message after removing mention",
                flush=True
            )

            await message.reply(
                "Haan bhai 😄 kya hua?",
                mention_author=False
            )

            return

        print(
            f"📝 AI QUESTION: {content}",
            flush=True
        )

        # --------------------------------------------------------
        # TYPING INDICATOR
        # --------------------------------------------------------

        try:

            async with message.channel.typing():

                # ------------------------------------------------
                # SEND OPENAI REQUEST
                # ------------------------------------------------

                print(
                    "🔄 Sending request to OpenAI...",
                    flush=True
                )

                response = await self.client.responses.create(

                    model="gpt-5-mini",

                    instructions=self.system_prompt,

                    input=content,

                    max_output_tokens=500
                )

                # ------------------------------------------------
                # GET RESPONSE
                # ------------------------------------------------

                reply = response.output_text.strip()

                print(
                    f"✅ OpenAI RESPONSE: {reply[:500]}",
                    flush=True
                )

                # ------------------------------------------------
                # EMPTY RESPONSE
                # ------------------------------------------------

                if not reply:

                    print(
                        "⚠️ OpenAI returned an empty response",
                        flush=True
                    )

                    reply = (
                        "Bhai mujhe response nahi mila 😅 "
                        "dobara try kar."
                    )

                # ------------------------------------------------
                # DISCORD MESSAGE LIMIT
                # ------------------------------------------------

                if len(reply) > 2000:

                    reply = reply[:1990] + "..."

                # ------------------------------------------------
                # SEND DISCORD MESSAGE
                # ------------------------------------------------

                await message.reply(
                    reply,
                    mention_author=False
                )

                print(
                    "✅ AI reply sent successfully",
                    flush=True
                )

        # --------------------------------------------------------
        # OPENAI / OTHER ERROR
        # --------------------------------------------------------

        except Exception as e:

            print(
                "==========================================",
                flush=True
            )

            print(
                "❌ AI ERROR",
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
                    f"❌ Could not send error message: "
                    f"{discord_error}",
                    flush=True
                )


# ============================================================
# COG SETUP
# ============================================================

async def setup(bot):

    await bot.add_cog(
        AICog(bot)
    )

    print(
        "✅ cogs.ai loaded successfully",
        flush=True
    )