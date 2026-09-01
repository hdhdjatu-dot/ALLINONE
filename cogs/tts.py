import discord, edge_tts, asyncio, re, os
from discord.ext import commands
from discord import app_commands

def clean_text(text: str):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()[:70]

class TTS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.on = {}
        self.tts_vc = {}
        self.queue = {}
        self.lock = {}

    @app_commands.command(name="join", description="VC me aao")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("Pehle VC join kar!", ephemeral=True)
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message(f"✅ {interaction.user.voice.channel.name} me aa gaya!", ephemeral=True)

    @app_commands.command(name="leave", description="VC se niklo")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("✅ Nikal gaya!", ephemeral=True)

    @app_commands.command(name="settts", description="Kis VC ka chat padhna hai")
    async def settts(self, interaction: discord.Interaction, vc: discord.VoiceChannel):
        self.tts_vc[interaction.guild.id] = vc.id
        await interaction.response.send_message(f"✅ Set! Ab **{vc.name}** ka chat padhunga", ephemeral=True)

    @app_commands.command(name="tts", description="TTS on/off")
    @app_commands.choices(mode=[app_commands.Choice(name="on", value="on"), app_commands.Choice(name="off", value="off")])
    async def tts_cmd(self, interaction: discord.Interaction, mode: str):
        self.on[interaction.guild.id] = mode == "on"
        await interaction.response.send_message(f"TTS {mode.upper()}!", ephemeral=True)

    async def play_tts_packet(self, vc, file_path):
        """Gana ka source delete kiye bina TTS bajayega"""
        try:
            source = discord.FFmpegPCMAudio(file_path)
            # thoda wait taaki ffmpeg start ho jaye
            await asyncio.sleep(0.2)
            while True:
                data = source.read()
                if not data:
                    break
                # encode=True se discord khud opus me convert kar dega
                vc.send_audio_packet(data, encode=True)
                await asyncio.sleep(0.02) # 20ms - discord ka frame size
            source.cleanup()
        except Exception as e:
            print(f"Packet play error: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        if not self.on.get(message.guild.id): return
        if not message.content: return
        vc = message.guild.voice_client
        if not vc: return

        gid = message.guild.id
        target_vc_id = self.tts_vc.get(gid) or vc.channel.id
        if message.channel.id!= target_vc_id: return

        cleaned = clean_text(message.content)
        if not cleaned: return

        if gid not in self.queue:
            self.queue[gid] = []
            self.lock[gid] = False

        self.queue[gid].append(f"{message.author.display_name} says {cleaned}")

        if self.lock[gid]: return
        self.lock[gid] = True

        while self.queue[gid]:
            text = self.queue[gid].pop(0)
            tts_file = f"tts_{gid}.mp3"

            try:
                await edge_tts.Communicate(text, voice="hi-IN-MadhurNeural", rate="+40%").save(tts_file)

                music_cog = self.bot.get_cog("Music")
                player = music_cog.get_player(gid) if music_cog else None

                if player and player.voice and player.voice.is_playing() and player.current:
                    original_vol = player.volume

                    # 1. Volume halka karo - 20% (slow wala feel)
                    try:
                        if player.voice.source and isinstance(player.voice.source, discord.PCMVolumeTransformer):
                            player.voice.source.volume = original_vol * 0.20
                    except: pass

                    await asyncio.sleep(0.15)

                    # 2. Gana PAUSE karo - STOP nahi, taaki source zinda rahe
                    player.voice.pause()
                    await asyncio.sleep(0.1)

                    # 3. TTS bajao - bina vc.play() ke, direct packet se
                    # Isse music ka source delete nahi hoga
                    await self.play_tts_packet(vc, tts_file)

                    await asyncio.sleep(0.1)

                    # 4. Wapas volume full aur RESUME - wahin se bajega
                    try:
                        if player.voice.source and isinstance(player.voice.source, discord.PCMVolumeTransformer):
                            player.voice.source.volume = original_vol
                        player.voice.resume()
                        print(f"[TTS] Resumed: {player.current.title}")
                    except Exception as e:
                        print(f"Resume error: {e}")

                else:
                    # Gana nahi baj raha to normal play
                    vc.play(discord.FFmpegPCMAudio(tts_file))
                    while vc.is_playing():
                        await asyncio.sleep(0.05)

            except Exception as e:
                print(f"TTS Error: {e}")
                import traceback
                traceback.print_exc()
                # Agar kuch gadbad hui to gana resume karne ki koshish karo
                try:
                    music_cog = self.bot.get_cog("Music")
                    player = music_cog.get_player(gid) if music_cog else None
                    if player and player.voice and player.voice.is_paused():
                        player.voice.resume()
                except: pass

        self.lock[gid] = False

async def setup(bot):
    await bot.add_cog(TTS(bot))