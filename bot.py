import os
import discord
from discord.ext import commands
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# 1. Setup Flask Web Server (For Render keeping it alive)
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    # Render provides a PORT environment variable automatically
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# 2. Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 3. Configure Google Gemini
genai.configure(api_key=GEMINI_API_KEY)
SYSTEM_INSTRUCTION = """
You are 'Aether', a highly advanced, intelligent, and witty AI companion.
You are chatting inside a Discord server. 
Keep your answers engaging, concise, and beautifully formatted using Discord Markdown.
"""

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

chat_sessions = {}

# 4. Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🚀 {bot.user.name} is online and running seamlessly!")
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
                    chat_sessions[channel_id] = model.start_chat(history=[])
                
                response = chat_sessions[channel_id].send_message(user_prompt)
                ai_reply = response.text

                if len(ai_reply) > 2000:
                    for i in range(0, len(ai_reply), 2000):
                        await message.channel.send(ai_reply[i:i+2000])
                else:
                    await message.reply(ai_reply)
            except Exception as e:
                print(f"Error: {e}")
                await message.channel.send("⚠️ Sorry, my circuits encountered an error.")

    await bot.process_commands(message)

# 5. Start Web Server and Run Bot
if __name__ == "__main__":
    keep_alive()  # Starts the background web server
    bot.run(DISCORD_TOKEN)
