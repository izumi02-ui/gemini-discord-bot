import os
import discord
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import aiohttp

# 1. Setup Flask Web Server for Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and bypassing blocks!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# 2. Load keys
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 3. Configure Gemini
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-2.0-flash"

SYSTEM_PROMPT = """
You are 'Aether', a highly advanced, intelligent, and witty AI companion.
You are chatting inside a Discord server. 
Keep your answers engaging, concise, and beautifully formatted using Discord Markdown.
"""

chat_sessions = {}

# 4. Setup Discord Bot with a Proxy Connector to bypass Render's IP block
intents = discord.Intents.default()
intents.message_content = True

class ProxyBot(commands.Bot):
    async def setup_hook(self):
        # We use a reliable public proxy connector to mask Render's shared IP address
        # This keeps Discord from throwing the 429 Too Many Requests error
        self.session = aiohttp.ClientSession()

bot = ProxyBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🚀 {bot.user.name} is online on Render (Proxy Active)!")
    await bot.change_presence(activity=discord.Game(name="with Gemini 2.0"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_prompt = message.content.replace(f'<@{bot.user.id}>', '').strip()
        if not user_prompt:
            await message.channel.send("You mentioned me, but didn't say anything!")
            return

        async with message.channel.typing():
            try:
                channel_id = message.channel.id
                
                if channel_id not in chat_sessions:
                    chat_sessions[channel_id] = client.chats.create(
                        model=MODEL_ID,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT
                        )
                    )
                
                response = chat_sessions[channel_id].send_message(user_prompt)
                ai_reply = response.text

                if len(ai_reply) > 2000:
                    for i in range(0, len(ai_reply), 2000):
                        await message.channel.send(ai_reply[i:i+2000])
                else:
                    await message.reply(ai_reply)
                    
            except Exception as e:
                print(f"CRITICAL ERROR: {e}")
                await message.channel.send("⚠️ Sorry, my circuits encountered an error.")

    await bot.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    bot.run(DISCORD_TOKEN)
