import discord
from discord.ext import commands
import requests
import urllib.parse
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

# Enable privileged intents (for message content)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Simple cache using a dictionary
song_cache = {}

# Helper function to generate a cache key
def make_cache_key(query: str):
    return hashlib.md5(query.lower().encode()).hexdigest()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command(name="wutsong")
async def wutsong(ctx, *, query):
    key = make_cache_key(query)

    if key in song_cache:
        print(f"📁 Cache hit for: {query}")
        result = song_cache[key]
    else:
        print(f"🌐 Searching for: {query}")
        url = "https://itunes.apple.com/search"
        params = {
            "term": query,
            "limit": 1,
            "media": "music"
        }
        response = requests.get(url, params=params)
        data = response.json()

        if data["resultCount"] == 0:
            await ctx.send("❌ No results found.")
            return

        result = data["results"][0]
        song_cache[key] = result

    # Extract song info
    track_name = result.get("trackName", "Unknown")
    artist_name = result.get("artistName", "Unknown")
    album_name = result.get("collectionName", "Unknown")
    preview_url = result.get("previewUrl")
    track_view_url = result.get("trackViewUrl")
    artwork = result.get("artworkUrl100", "").replace("100x100bb", "512x512bb")

    # Extra links (search on YouTube/Spotify)
    youtube_query = urllib.parse.quote_plus(f"{track_name} {artist_name}")
    spotify_query = urllib.parse.quote_plus(f"{track_name} {artist_name}")
    youtube_url = f"https://www.youtube.com/results?search_query={youtube_query}"
    spotify_url = f"https://open.spotify.com/search/{spotify_query}"

    # Build embed
    embed = discord.Embed(
        title=track_name,
        url=track_view_url,
        description=f"🎤 **{artist_name}**\n💿 *{album_name}*",
        color=0x1DB954
    )
    embed.set_thumbnail(url=artwork)

    if preview_url:
        embed.add_field(name="▶️ Preview", value=f"[Listen]({preview_url})", inline=False)

    embed.add_field(name="🔗 YouTube", value=f"[Search]({youtube_url})", inline=True)
    embed.add_field(name="🔗 Spotify", value=f"[Search]({spotify_url})", inline=True)

    await ctx.send(embed=embed)
    

# Replace 'YOUR_BOT_TOKEN' with your actual Discord bot token
bot.run(os.getenv("DISCORD_TOKEN"))