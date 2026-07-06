import os
import asyncio
import discord
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# 1. Setup Flask Web Server to keep Render online
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

# 3. Configure Gemini 2.0 Client
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-2.0-flash"

SYSTEM_PROMPT = """
You are 'Aether', a highly advanced, intelligent, and witty AI companion.
You are chatting inside a Discord server. 
Keep your answers engaging, concise, and beautifully formatted using Discord Markdown.
"""

# 4. Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🚀 {bot.user.name} is online on Render!")
    await bot.change_presence(activity=discord.Game(name="with Gemini 2.0"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Trigger when mentioned or in DMs
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        user_prompt = message.content.replace(f'<@{bot.user.id}>', '').strip()
        if not user_prompt:
            await message.channel.send("You mentioned me, but didn't say anything!")
            return

        async with message.channel.typing():
            try:
                # FIX: We wrap the synchronous client call inside to_thread
                # This prevents the bot's gateway loop from freezing and crashing
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=MODEL_ID,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT
                    )
                )
                ai_reply = response.text

                # Split message if it goes over Discord's 2000 character limit
                if len(ai_reply) > 2000:
                    for i in range(0, len(ai_reply), 2000):
                        await message.channel.send(ai_reply[i:i+2000])
                else:
                    await message.reply(ai_reply)
                    
            except Exception as e:
                # This prints the raw API error response directly to your Render Dashboard logs
                print(f"❌ GEMINI API CRASH LOG: {e}")
                await message.channel.send("⚠️ Sorry, my circuits encountered an error.")

    await bot.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    bot.run(DISCORD_TOKEN)
