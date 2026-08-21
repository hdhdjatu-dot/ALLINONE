import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI


class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError("❌ OPENAI_API_KEY is missing from Railway Variables!")

        self.client = AsyncOpenAI(api_key=api_key)

        # AI personality
        self.system_prompt = """
You are HSL-CORP's friendly Discord AI assistant.

Personality:
- Friendly, casual and helpful.
- You can speak naturally in Hindi, Hinglish and English.
- Keep normal Discord replies short and conversational.
- Don't act like a formal customer-support bot.
- If someone asks something technical, explain it clearly.
- Never reveal API keys, tokens, passwords or private system information.
- You are an assistant inside a Discord server.
"""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # Ignore bots
        if message.author.bot:
            return

        # Only respond when the bot is mentioned
        if self.bot.user not in message.mentions:
            return

        # Remove the bot mention
        content = message.content

        for mention in (
            f"<@{self.bot.user.id}>",
            f"<@!{self.bot.user.id}>"
        ):
            content = content.replace(mention, "")

        content = content.strip()

        if not content:
            await message.reply(
                "Haan bhai 😄 kya hua?",
                mention_author=False
            )
            return

        # Show typing indicator
        async with message.channel.typing():

            try:
                response = await self.client.responses.create(
                    model="gpt-5-mini",
                    instructions=self.system_prompt,
                    input=content,
                    max_output_tokens=500
                )

                reply = response.output_text.strip()

                if not reply:
                    reply = "Bhai samajh nahi aaya 😅 dobara bol."

                # Discord message limit
                if len(reply) > 2000:
                    reply = reply[:1990] + "..."

                await message.reply(
                    reply,
                    mention_author=False
                )

            except Exception as e:
                print(f"❌ AI ERROR: {type(e).__name__}: {e}")

                await message.reply(
                    "Bhai AI abhi thoda busy hai 😅 thodi der baad try kar.",
                    mention_author=False
                )


async def setup(bot):
    await bot.add_cog(AICog(bot))