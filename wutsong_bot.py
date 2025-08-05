import discord
from discord.ext import commands
import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import cohere

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

co = cohere.Client(COHERE_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cache and user tracking
db_cache = {}
user_last_song = {}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# Function to get lyrics snippet from Genius
def get_lyrics_snippet(artist, title):
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    search_url = "https://api.genius.com/search"
    params = {"q": f"{title} {artist}"}
    response = requests.get(search_url, params=params, headers=headers)

    if response.status_code != 200:
        print(f"Genius API error: {response.status_code}")
        return None

    hits = response.json()["response"]["hits"]
    if not hits:
        print("No Genius search results.")
        return None

    song_url = hits[0]["result"]["url"]
    print(f"Genius song URL: {song_url}")
    lyrics_page = requests.get(song_url)
    soup = BeautifulSoup(lyrics_page.text, "html.parser")

    lyrics_blocks = soup.select("div[class^='Lyrics__Container']")

    if not lyrics_blocks:
        print("No lyrics containers found.")
        return None

    lyrics = "\n".join(block.get_text(strip=True, separator="\n") for block in lyrics_blocks)
    return lyrics

@bot.command(name="wutsong")
async def wutsong(ctx, *, query):
    key = query.lower()

    if key in db_cache:
        result = db_cache[key]
    else:
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
        db_cache[key] = result

    track_name = result.get("trackName")
    artist_name = result.get("artistName")
    album_name = result.get("collectionName")
    preview_url = result.get("previewUrl")
    track_view_url = result.get("trackViewUrl")
    artwork = result.get("artworkUrl100", "").replace("100x100bb", "512x512bb")

    user_last_song[ctx.author.id] = (track_name, artist_name)

    lyrics_snippet = get_lyrics_snippet(artist_name, track_name)

    embed = discord.Embed(
        title=track_name,
        url=track_view_url,
        description=f"🎤 {artist_name}\n💿 {album_name}",
        color=0x1DB954
    )
    embed.set_thumbnail(url=artwork)

    if preview_url:
        embed.add_field(name="▶️ Preview", value=f"[Listen]({preview_url})", inline=False)

    youtube_query = requests.utils.quote(f"{track_name} {artist_name}")
    spotify_query = youtube_query

    embed.add_field(name="🔗 YouTube", value=f"[Search](https://www.youtube.com/results?search_query={youtube_query})", inline=True)
    embed.add_field(name="🔗 Spotify", value=f"[Search](https://open.spotify.com/search/{spotify_query})", inline=True)

    if lyrics_snippet:
        embed.add_field(name="📝 Lyrics (snippet)", value=f"> {lyrics_snippet[:200]}...", inline=False)

    await ctx.send(embed=embed)

@bot.command(name="wutlyrics")
async def wutlyrics(ctx, *, query=None):
    async with ctx.typing():
        try:
            await ctx.send("🔍 Searching for lyrics...")

            if not query:
                if ctx.author.id in user_last_song:
                    title, artist = user_last_song[ctx.author.id]
                else:
                    await ctx.send("❗ Please specify a song name or use `!wutsong` first.")
                    return
            else:
                if " - " in query:
                    artist, title = query.split(" - ", 1)
                else:
                    artist, title = "", query

            print(f"Searching Genius for artist: '{artist}', title: '{title}'")
            lyrics = get_lyrics_snippet(artist, title)

            if not lyrics:
                await ctx.send("❌ Could not find lyrics.")
                return

            if len(lyrics) > 1900:
                with open("lyrics.txt", "w", encoding="utf-8") as f:
                    f.write(lyrics)
                await ctx.send("📄 Lyrics are too long for chat. See attached file:", file=discord.File("lyrics.txt"))
            else:
                await ctx.send(f"📝 **Lyrics for:** `{title}`\n\n{lyrics}")

        except Exception as e:
            print(f"Error in !wutlyrics: {e}")
            await ctx.send(f"⚠️ Error getting lyrics: {str(e)}")

@bot.command(name="wutguess")
async def wutguess(ctx, *, hint):
    await ctx.send("🧠 Thinking really hard...")
    try:
        prompt = (
            "You're a music expert. Given the following vague hint or description, guess the most likely song title and artist.\n"
            f"Hint: {hint}\n"
            "Answer in this format: Song Title by Artist Name."
        )

        response = co.generate(
            model="command-r",
            prompt=prompt,
            max_tokens=50,
            temperature=0.8
        )
        guess = response.generations[0].text.strip()

        if guess:
            await ctx.send(f"🎯 I think you're thinking of: {guess}")
        else:
            await ctx.send("❌ I couldn’t make a good guess. Try rephrasing it!")
    except Exception as e:
        print(f"Cohere API error: {e}")
        await ctx.send("⚠️ Something went wrong while guessing. Please try again later!")

bot.run(DISCORD_TOKEN)
