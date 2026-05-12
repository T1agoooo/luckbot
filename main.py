import discord
from discord.ext import commands
import random
import os
from pymongo import MongoClient

# ---- CONFIGURATION ----
TOKEN = os.environ.get("TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
LUCK_CHANNEL_NAME = "🍀・luck-roll"
BOOSTER_ROLE_NAME = "Server Booster"
# ------------------------

client = MongoClient(MONGO_URL)
db = client["luckbot"]
users_col = db["users"]

ROLES = [
    "Common I", "Common II", "Common III",
    "Uncommon I", "Uncommon II", "Uncommon III",
    "Rare I", "Rare II", "Rare III",
    "Epic I", "Epic II", "Epic III",
    "Legendary I", "Legendary II", "Legendary III",
    "Mythic I", "Mythic II", "Mythic III",
    "Divine I", "Divine II", "Divine III",
    "Celestial I", "Celestial II", "Celestial III",
    "Eternal I", "Eternal II", "Eternal III",
]

ROLE_CHANCES = {
    "Common I":      33333333,
    "Common II":     16666666,
    "Common III":    10000000,
    "Uncommon I":    5000000,
    "Uncommon II":   2500000,
    "Uncommon III":  1333333,
    "Rare I":        666666,
    "Rare II":       333333,
    "Rare III":      166666,
    "Epic I":        100000,
    "Epic II":       50000,
    "Epic III":      25000,
    "Legendary I":   14285,
    "Legendary II":  6666,
    "Legendary III": 3333,
    "Mythic I":      2000,
    "Mythic II":     1333,
    "Mythic III":    1000,
    "Divine I":      666,
    "Divine II":     400,
    "Divine III":    200,
    "Celestial I":   133,
    "Celestial II":  100,
    "Celestial III": 50,
    "Eternal I":     20,
    "Eternal II":    10,
    "Eternal III":   1,
}

ROLE_DISPLAY_CHANCES = {
    "Common I":      "1 in 3",
    "Common II":     "1 in 6",
    "Common III":    "1 in 10",
    "Uncommon I":    "1 in 20",
    "Uncommon II":   "1 in 40",
    "Uncommon III":  "1 in 75",
    "Rare I":        "1 in 150",
    "Rare II":       "1 in 300",
    "Rare III":      "1 in 600",
    "Epic I":        "1 in 1,000",
    "Epic II":       "1 in 2,000",
    "Epic III":      "1 in 4,000",
    "Legendary I":   "1 in 7,000",
    "Legendary II":  "1 in 15,000",
    "Legendary III": "1 in 30,000",
    "Mythic I":      "1 in 50,000",
    "Mythic II":     "1 in 75,000",
    "Mythic III":    "1 in 100,000",
    "Divine I":      "1 in 150,000",
    "Divine II":     "1 in 250,000",
    "Divine III":    "1 in 500,000",
    "Celestial I":   "1 in 750,000",
    "Celestial II":  "1 in 1,000,000",
    "Celestial III": "1 in 2,000,000",
    "Eternal I":     "1 in 5,000,000",
    "Eternal II":    "1 in 10,000,000",
    "Eternal III":   "1 in 100,000,000",
}

ITEMS = {
    "Lucky Dice":         {"chance": 2000000,  "boost": 5,    "emoji": "🎲"},
    "Golden Lucky Dice":  {"chance": 200000,   "boost": 25,   "emoji": "🟡🎲"},
    "Diamond Lucky Dice": {"chance": 100000,   "boost": 100,  "emoji": "💎🎲"},
    "Cosmic Lucky Dice":  {"chance": 10000,    "boost": 1000, "emoji": "🌌🎲"},
}

PROGRESS_EMOJIS = ["🟩", "🟩", "🟩", "🟩", "🟩"]
EMPTY_EMOJI = "⬜"

def get_user(user_id):
    uid = str(user_id)
    user = users_col.find_one({"_id": uid})
    if not user:
        user = {"_id": uid, "pity": {}, "inventory": {}, "active_boost": None, "best_roll": None}
        users_col.insert_one(user)
    if "best_roll" not in user:
        user["best_roll"] = None
    return user

def save_user(user):
    users_col.replace_one({"_id": user["_id"]}, user, upsert=True)

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

    user = get_user(ctx.author.id)
    is_booster = discord.utils.get(ctx.author.roles, name=BOOSTER_ROLE_NAME) is not None
    luck_multiplier = 1.5 if is_booster else 1.0
    drop_multiplier = 1.25 if is_booster else 1.0

    if user["active_boost"]:
        boost_name = user["active_boost"]
        luck_multiplier *= ITEMS[boost_name]["boost"]
        user["active_boost"] = None

    roll = random.randint(1, 100000000)
    effective_roll = roll / luck_multiplier

    got_item = None
    for item_name, item_data in ITEMS.items():
        adjusted_chance = item_data["chance"] * drop_multiplier
        if effective_roll <= adjusted_chance:
            inv = user["inventory"]
            inv[item_name] = inv.get(item_name, 0) + 1
            got_item = item_name
            break

    won_role = None
    cumulative = 0
    for role_name, chance in ROLE_CHANCES.items():
        cumulative += chance
        if effective_roll <= cumulative:
            won_role = role_name
            break

    if won_role:
        pity = user["pity"]
        pity[won_role] = pity.get(won_role, 0) + 1
        count = pity[won_role]

        # Update best roll
        if user["best_roll"] is None or ROLES.index(won_role) > ROLES.index(user["best_roll"]):
            user["best_roll"] = won_role

        role_obj = discord.utils.get(ctx.guild.roles, name=won_role)
        if role_obj and role_obj not in ctx.author.roles:
            await ctx.author.add_roles(role_obj)

        if count >= 5:
            pity[won_role] = 0
            role_index = ROLES.index(won_role)
            if role_index + 1 < len(ROLES):
                next_role_name = ROLES[role_index + 1]
                next_role_obj = discord.utils.get(ctx.guild.roles, name=next_role_name)
                if next_role_obj:
                    await ctx.author.add_roles(next_role_obj)
                pity[next_role_name] = pity.get(next_role_name, 0) + 1
                await ctx.send(
                    f"🎉 **UPGRADE!** {ctx.author.mention} collected enough **{won_role}** to evolve into **{next_role_name}**! 🚀"
                )
            else:
                await ctx.send(f"✨ {ctx.author.mention} You already have the max role and got **{won_role}** again!")
        else:
            filled = "".join([PROGRESS_EMOJIS[i] if i < count else EMPTY_EMOJI for i in range(5)])
            await ctx.send(
                f"🎊 {ctx.author.mention} You got **{won_role}**!\n"
                f"Progress: {filled} ({count}/5) — collect {5 - count} more to upgrade!"
            )
    else:
        await ctx.send(f"🍃 {ctx.author.mention} You found nothing...")

    if got_item:
        item = ITEMS[got_item]
        await ctx.send(f"{item['emoji']} {ctx.author.mention} You also found a **{got_item}**! Added to your inventory.")

    save_user(user)

@bot.command(name="use")
async def use_item(ctx, *, item_name: str):
    if ctx.channel.name != LUCK_CHANNEL_NAME:
        return

    user = get_user(ctx.author.id)
    inv = user["inventory"]

    matched = None
    for name in ITEMS:
        if name.lower() == item_name.lower():
            matched = name
            break

    if not matched or inv.get(matched, 0) == 0:
        await ctx.send(f"❌ {ctx.author.mention} You don't have that item.")
        save_user(user)
        return

    inv[matched] -= 1
    if inv[matched] == 0:
        del inv[matched]

    user["active_boost"] = matched
    boost = ITEMS[matched]["boost"]
    emoji = ITEMS[matched]["emoji"]
    await ctx.send(f"{emoji} {ctx.author.mention} Used **{matched}**! Your next `?luck` roll has **{boost}x** luck boost! 🍀")
    save_user(user)

@bot.command(name="inv")
async def inventory(ctx):
    user = get_user(ctx.author.id)
    inv = user["inventory"]
    active = user["active_boost"]

    if not inv and not active:
        await ctx.send(f"🎒 {ctx.author.mention} Your inventory is empty!")
        return

    lines = [f"🎒 **{ctx.author.display_name}'s Inventory:**\n"]
    for item_name, count in inv.items():
        emoji = ITEMS[item_name]["emoji"]
        lines.append(f"{emoji} **{item_name}** x{count}")

    if active:
        emoji = ITEMS[active]["emoji"]
        lines.append(f"\n⚡ **Active Boost:** {emoji} {active} ({ITEMS[active]['boost']}x) — ready for next roll!")

    await ctx.send("\n".join(lines))

@bot.command(name="lb")
async def leaderboard(ctx):
    all_users = list(users_col.find({"best_roll": {"$ne": None}}))

    if not all_users:
        await ctx.send("🏆 No one has rolled anything yet!")
        return

    # Sort by best roll index
    all_users.sort(key=lambda u: ROLES.index(u["best_roll"]), reverse=True)
    top = all_users[:10]

    lines = ["🏆 **LUCK LEADERBOARD — TOP 10**\n"]
    medals = ["🥇", "🥈", "🥉"]

    for i, u in enumerate(top):
        member = ctx.guild.get_member(int(u["_id"]))
        name = member.display_name if member else f"Unknown ({u['_id']})"
        best = u["best_roll"]
        chance = ROLE_DISPLAY_CHANCES[best]
        medal = medals[i] if i < 3 else f"**#{i+1}**"
        lines.append(f"{medal} {name} — **{best}** *(chance: {chance})*")

    await ctx.send("\n".join(lines))

bot.run(TOKEN)
