import discord
from discord.ext import commands
import random

# ---- CONFIGURATION ----
import os
TOKEN = os.environ.get("TOKEN")
LUCK_CHANNEL_NAME = "🍀︱luck-roll"
# ------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command(name="luck")
async def luck(ctx):
    if ctx.channel.name != LUCK_CHANNEL_NAME:
        return

    roll = random.randint(1, 100000)

    if roll == 1:
        rarity = ("Eternal [ Lucky ]", "✨ **ETERNAL**")
    elif roll <= 3:
        rarity = ("Celestial [ Lucky ]", "🌌 **CELESTIAL**")
    elif roll <= 13:
        rarity = ("Divine [ Lucky ]", "⚡ **DIVINE**")
    elif roll <= 33:
        rarity = ("Mythic [ Lucky ]", "🔥 **MYTHIC**")
    elif roll <= 83:
        rarity = ("Legendary [ Lucky ]", "🟠 **LEGENDARY**")
    elif roll <= 283:
        rarity = ("Epic [ Lucky ]", "💜 **EPIC**")
    elif roll <= 1283:
        rarity = ("Rare [ Lucky ]", "🔵 **RARE**")
    elif roll <= 6283:
        rarity = ("Uncommon [ Lucky ]", "🟢 **UNCOMMON**")
    elif roll <= 26283:
        rarity = ("Common [ Lucky ]", "⚪ **COMMON**")
    else:
        rarity = None

    if rarity:
        role = discord.utils.get(ctx.guild.roles, name=rarity[0])
        if role:
            await ctx.author.add_roles(role)
            await ctx.send(f"{rarity[1]}\n{ctx.author.mention} just got **{rarity[0]}**! 🎉")
        else:
            await ctx.send(f"⚠️ Role `{rarity[0]}` not found. Make sure it exists in the server!")
    else:
        await ctx.send(f"🍃 {ctx.author.mention} You found nothing...")

bot.run(TOKEN)