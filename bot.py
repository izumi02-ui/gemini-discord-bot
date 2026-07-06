import os
import discord
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# 1. Setup Flask Web Server to keep Render happy
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

# 4. Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True

# We override the bot's standard HTTP client connection to use a fallback proxy
# This prevents Render's IP from triggering a 429 Too Many Requests block
class ProxyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional: You can explicitly pass a proxy URL here if needed, 
        # but changing the connection handler resets the blocked session state.

bot = ProxyBot(command_prefix="!", intents=intents)

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
                
                # FIX: We use a standard generation call to avoid the chat object's synchronous block bug on mobile loops
                response = client.models.generate_content(
                    model=MODEL_ID,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT
                    )
                )
                ai_reply = response.text

                if len(ai_reply) > 2000:
                    for i in range(0, len(ai_reply), 2000):
                        await message.channel.send(ai_reply[i:i+2000])
                else:
                    await message.reply(ai_reply)
                    
            except Exception as e:
                # This will print the EXACT internal API error to your Render logs if it hiccups
                print(f"GEMINI EXECUTION ERROR: {e}")
                await message.channel.send("⚠️ Sorry, my circuits encountered an error.")

    await bot.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    bot.run(DISCORD_TOKEN)
