import discord
from discord.ext import commands
import random
import os
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

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

DICE = {
    "Lucky Dice":         {"boost": 5,    "emoji": "🎲"},
    "Golden Lucky Dice":  {"boost": 25,   "emoji": "🟡🎲"},
    "Diamond Lucky Dice": {"boost": 100,  "emoji": "💎🎲"},
    "Cosmic Lucky Dice":  {"boost": 1000, "emoji": "🌌🎲"},
}

MATERIALS = {
    "Shard":     {"chance": 40000000, "emoji": "🔹"},
    "Crystal":   {"chance": 20000000, "emoji": "💠"},
    "Essence":   {"chance": 8000000,  "emoji": "🌀"},
    "Rune":      {"chance": 3000000,  "emoji": "🔮"},
    "Sigil":     {"chance": 1000000,  "emoji": "⚜️"},
    "Void Core": {"chance": 200000,   "emoji": "🌑"},
}

RECIPES = {
    "Lucky Dice": {
        "emoji": "🎲",
        "boost": "5x",
        "materials": {"Shard": 10, "Crystal": 5}
    },
    "Golden Lucky Dice": {
        "emoji": "🟡🎲",
        "boost": "25x",
        "materials": {"Crystal": 10, "Essence": 5, "Rune": 2}
    },
    "Diamond Lucky Dice": {
        "emoji": "💎🎲",
        "boost": "100x",
        "materials": {"Essence": 10, "Rune": 8, "Sigil": 3}
    },
    "Cosmic Lucky Dice": {
        "emoji": "🌌🎲",
        "boost": "1000x",
        "materials": {"Sigil": 10, "Void Core": 5, "Rune": 15}
    },
}

PROGRESS_EMOJIS = ["🟩", "🟩", "🟩", "🟩", "🟩"]
EMPTY_EMOJI = "⬜"

def get_user(user_id):
    uid = str(user_id)
    user = users_col.find_one({"_id": uid})
    if not user:
        user = {
            "_id": uid,
            "pity": {},
            "inventory": {},
            "active_boosts": [],
            "best_roll": None,
            "rolls": 0,
            "rebirths": 0,
            "last_daily": None,
        }
        try:
            users_col.insert_one(user)
        except:
            user = users_col.find_one({"_id": uid})
    for field, default in [
        ("best_roll", None), ("rolls", 0), ("rebirths", 0),
        ("last_daily", None), ("active_boosts", [])
    ]:
        if field not in user:
            user[field] = default
    if "active_boost" in user:
        old = user.pop("active_boost")
        if old and old not in user["active_boosts"]:
            user["active_boosts"].append(old)
    return user

def save_user(user):
    users_col.replace_one({"_id": user["_id"]}, user, upsert=True)

def get_total_boost(active_boosts):
    total = 1.0
    for dice_name in active_boosts:
        if dice_name in DICE:
            total *= DICE[dice_name]["boost"]
    return total

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

    rebirths = user.get("rebirths", 0)
    if rebirths > 0:
        luck_multiplier *= (2 ** rebirths)

    active_boosts = user.get("active_boosts", [])
    if active_boosts:
        dice_boost = get_total_boost(active_boosts)
        luck_multiplier *= dice_boost
        boost_str = " × ".join([f"{DICE[d]['emoji']} {DICE[d]['boost']}x" for d in active_boosts])
        user["active_boosts"] = []
    else:
        boost_str = None

    user["rolls"] = user.get("rolls", 0) + 1
    total_rolls = user["rolls"]

    effective_roll = random.randint(1, 100000000) / luck_multiplier
effective_roll = max(1, int(effective_roll))

    dropped_materials = {}
    for mat_name, mat_data in MATERIALS.items():
        adjusted_chance = int(mat_data["chance"] * drop_multiplier)
        mat_roll = random.randint(1, 100000000)
        if mat_roll <= adjusted_chance:
            inv = user["inventory"]
            inv[mat_name] = inv.get(mat_name, 0) + 1
            dropped_materials[mat_name] = mat_data["emoji"]

    got_dice = None
    dice_drop_chances = {
        "Lucky Dice":         2000000,
        "Golden Lucky Dice":  200000,
        "Diamond Lucky Dice": 100000,
        "Cosmic Lucky Dice":  10000,
    }
    for dice_name, chance in dice_drop_chances.items():
        adjusted_chance = int(chance * drop_multiplier / luck_multiplier)  # FIX: apply luck_multiplier
        if effective_roll <= adjusted_chance:
            inv = user["inventory"]
            inv[dice_name] = inv.get(dice_name, 0) + 1
            got_dice = dice_name
            break

    won_role = None
    cumulative = 0
    for role_name, chance in ROLE_CHANCES.items():
        cumulative += int(chance / luck_multiplier)  # FIX: scale thresholds by luck_multiplier
        if effective_roll <= cumulative:
            won_role = role_name
            break

    msg_parts = []

    if boost_str:
        msg_parts.append(f"⚡ **Boost active:** {boost_str} = **{luck_multiplier:.0f}x total**")

    if won_role:
        pity = user["pity"]
        pity[won_role] = pity.get(won_role, 0) + 1
        count = pity[won_role]

        current_best = user.get("best_roll")
        if current_best is None or ROLES.index(won_role) > ROLES.index(current_best):
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
                if user["best_roll"] is None or ROLES.index(next_role_name) > ROLES.index(user["best_roll"]):
                    user["best_roll"] = next_role_name
                msg_parts.append(
                    f"🎉 **UPGRADE!** {ctx.author.mention} evolved **{won_role}** → **{next_role_name}**! 🚀\n"
                    f"─────────────────\n"
                    f"🎲 Total rolls: **{total_rolls:,}**"
                )
            else:
                msg_parts.append(
                    f"✨ {ctx.author.mention} Max role reached! Got **{won_role}** again!\n"
                    f"─────────────────\n"
                    f"🎲 Total rolls: **{total_rolls:,}**"
                )
        else:
            filled = "".join([PROGRESS_EMOJIS[i] if i < count else EMPTY_EMOJI for i in range(5)])
            msg_parts.append(
                f"🎊 {ctx.author.mention} You got **{won_role}**!\n"
                f"Progress: {filled} ({count}/5) — {5 - count} more to upgrade!\n"
                f"─────────────────\n"
                f"🎲 Total rolls: **{total_rolls:,}**"
            )
    else:
        msg_parts.append(
            f"🍃 {ctx.author.mention} You found nothing...\n"
            f"─────────────────\n"
            f"🎲 Total rolls: **{total_rolls:,}**"
        )

    if got_dice:
        emoji = DICE[got_dice]["emoji"]
        msg_parts.append(f"{emoji} You also found a **{got_dice}**! Added to your inventory.")

    if dropped_materials:
        mat_str = ", ".join([f"{emoji} **{name}**" for name, emoji in dropped_materials.items()])
        msg_parts.append(f"📦 Materials dropped: {mat_str}")

    await ctx.send("\n".join(msg_parts))
    save_user(user)

@bot.command(name="use")
async def use_item(ctx, *, item_name: str):
    if ctx.channel.name != LUCK_CHANNEL_NAME:
        return

    user = get_user(ctx.author.id)
    inv = user["inventory"]

    matched = None
    for name in DICE:
        if name.lower() == item_name.lower():
            matched = name
            break

    if not matched or inv.get(matched, 0) == 0:
        await ctx.send(f"❌ {ctx.author.mention} You don't have that item.")
        save_user(user)
        return

    if matched in user["active_boosts"]:
        await ctx.send(f"❌ {ctx.author.mention} You already have a **{matched}** active! Use `?luck` first to consume it.")
        return

    inv[matched] -= 1
    if inv[matched] == 0:
        del inv[matched]

    user["active_boosts"].append(matched)
    current_total = get_total_boost(user["active_boosts"])
    boost = DICE[matched]["boost"]
    emoji = DICE[matched]["emoji"]
    await ctx.send(
        f"{emoji} {ctx.author.mention} Used **{matched}** ({boost}x)!\n"
        f"⚡ Total active boost: **{current_total:.0f}x** — will apply on your next `?luck`!"
    )
    save_user(user)

@bot.command(name="inv")
async def inventory(ctx):
    user = get_user(ctx.author.id)
    inv = user["inventory"]
    active_boosts = user.get("active_boosts", [])

    if not inv and not active_boosts:
        await ctx.send(f"🎒 {ctx.author.mention} Your inventory is empty!")
        return

    lines = [f"🎒 **{ctx.author.display_name}'s Inventory:**\n"]

    for dice_name in DICE:
        count = inv.get(dice_name, 0)
        if count > 0:
            lines.append(f"{DICE[dice_name]['emoji']} **{dice_name}** x{count}")

    for mat_name, mat_data in MATERIALS.items():
        count = inv.get(mat_name, 0)
        if count > 0:
            lines.append(f"{mat_data['emoji']} **{mat_name}** x{count}")

    if active_boosts:
        total = get_total_boost(active_boosts)
        boost_str = " × ".join([f"{DICE[d]['emoji']} {d}" for d in active_boosts])
        lines.append(f"\n⚡ **Active Boosts:** {boost_str} = **{total:.0f}x total**")

    await ctx.send("\n".join(lines))

@bot.command(name="craftinfo")
async def craftinfo(ctx):
    lines = ["⚒️ **CRAFT RECIPES**\n"]
    for item_name, data in RECIPES.items():
        mats = ", ".join([f"{MATERIALS[m]['emoji']} **{m}** x{amt}" for m, amt in data["materials"].items()])
        lines.append(f"{data['emoji']} **{item_name}** ({data['boost']} luck boost)\n  └ {mats}\n")
    await ctx.send("\n".join(lines))

@bot.command(name="craft")
async def craft(ctx, *, item_name: str):
    if ctx.channel.name != LUCK_CHANNEL_NAME:
        return

    user = get_user(ctx.author.id)
    inv = user["inventory"]

    matched = None
    for name in RECIPES:
        if name.lower() == item_name.lower():
            matched = name
            break

    if not matched:
        await ctx.send(f"❌ {ctx.author.mention} That item doesn't exist. Use `?craftinfo` to see all recipes!")
        return

    recipe = RECIPES[matched]
    missing = []
    for mat, amount in recipe["materials"].items():
        if inv.get(mat, 0) < amount:
            missing.append(f"{MATERIALS[mat]['emoji']} **{mat}** (have {inv.get(mat, 0)}, need {amount})")

    if missing:
        await ctx.send(f"❌ {ctx.author.mention} Not enough materials!\nMissing: {', '.join(missing)}")
        return

    for mat, amount in recipe["materials"].items():
        inv[mat] -= amount
        if inv[mat] == 0:
            del inv[mat]

    inv[matched] = inv.get(matched, 0) + 1
    await ctx.send(f"{recipe['emoji']} {ctx.author.mention} Successfully crafted **{matched}**! Use it with `?use {matched.lower()}`!")
    save_user(user)

@bot.command(name="rebirth")
async def rebirth(ctx):
    if ctx.channel.name != LUCK_CHANNEL_NAME:
        return

    user = get_user(ctx.author.id)
    rolls = user.get("rolls", 0)
    rebirths = user.get("rebirths", 0)
    required = (rebirths + 1) * 1000

    if rolls < required:
        remaining = required - rolls
        await ctx.send(f"🔄 {ctx.author.mention} You need **{required:,} rolls** to rebirth. You have **{rolls:,}** — **{remaining:,}** more to go!")
        return

    user["rebirths"] = rebirths + 1
    new_multiplier = 2 ** (rebirths + 1)
    await ctx.send(
        f"🌟 **REBIRTH!** {ctx.author.mention} has rebirthed **{user['rebirths']}** time(s)!\n"
        f"Your luck multiplier from rebirths is now **{new_multiplier}x**! 🍀"
    )
    save_user(user)

@bot.command(name="daily")
async def daily(ctx):
    if ctx.channel.name != LUCK_CHANNEL_NAME:
        return

    user = get_user(ctx.author.id)
    now = datetime.now(timezone.utc)
    last = user.get("last_daily")

    if last:
        last_dt = datetime.fromisoformat(last)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        diff = now - last_dt
        if diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - diff
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes = remainder // 60
            await ctx.send(f"⏰ {ctx.author.mention} Already claimed! Come back in **{hours}h {minutes}m**.")
            return

    inv = user["inventory"]
    inv["Lucky Dice"] = inv.get("Lucky Dice", 0) + 1
    user["last_daily"] = now.isoformat()
    await ctx.send(f"🎲 {ctx.author.mention} You claimed your daily **Lucky Dice**! Use it with `?use lucky dice` for 5x luck. Come back tomorrow!")
    save_user(user)

@bot.command(name="profile")
async def profile(ctx, member: discord.Member = None):
    target = member or ctx.author
    user = get_user(target.id)

    rolls = user.get("rolls", 0)
    rebirths = user.get("rebirths", 0)
    best = user.get("best_roll") or "None"
    chance = ROLE_DISPLAY_CHANCES.get(best, "—") if best != "None" else "—"
    inv = user.get("inventory", {})
    active_boosts = user.get("active_boosts", [])

    dice_summary = ", ".join([f"{DICE[d]['emoji']} {d} x{inv[d]}" for d in inv if d in DICE and inv[d] > 0]) or "None"
    mat_summary = ", ".join([f"{MATERIALS[m]['emoji']} {m} x{inv[m]}" for m in inv if m in MATERIALS and inv[m] > 0]) or "None"
    boost_str = f"{get_total_boost(active_boosts):.0f}x ({', '.join(active_boosts)})" if active_boosts else "None"

    lines = [
        f"🍀 **{target.display_name}'s Profile**\n",
        f"🎲 **Rolls:** {rolls:,}",
        f"🌟 **Rebirths:** {rebirths}",
        f"🏆 **Best Roll:** {best} *({chance})*",
        f"─────────────────",
        f"🎲 **Dice:** {dice_summary}",
        f"📦 **Materials:** {mat_summary}",
        f"⚡ **Active Boost:** {boost_str}",
    ]
    await ctx.send("\n".join(lines))

@bot.command(name="serverstats")
async def serverstats(ctx):
    all_users = list(users_col.find({}))

    total_rolls = sum(u.get("rolls", 0) for u in all_users)
    total_rebirths = sum(u.get("rebirths", 0) for u in all_users)
    total_players = len(all_users)

    best_user = None
    best_index = -1
    for u in all_users:
        if u.get("best_roll"):
            idx = ROLES.index(u["best_roll"])
            if idx > best_index:
                best_index = idx
                best_user = u

    if best_user:
        member = ctx.guild.get_member(int(best_user["_id"]))
        best_name = member.display_name if member else "Unknown"
        best_role = best_user["best_roll"]
        best_chance = ROLE_DISPLAY_CHANCES[best_role]
        rarest_str = f"**{best_role}** by {best_name} *({best_chance})*"
    else:
        rarest_str = "Nobody has rolled anything yet!"

    lines = [
        f"📊 **SERVER LUCK STATS**\n",
        f"👥 **Total Players:** {total_players:,}",
        f"🎲 **Total Rolls:** {total_rolls:,}",
        f"🌟 **Total Rebirths:** {total_rebirths:,}",
        f"🏆 **Rarest Roll Ever:** {rarest_str}",
    ]
    await ctx.send("\n".join(lines))

@bot.command(name="lb")
async def leaderboard(ctx, category: str = "rolls"):
    all_users = list(users_col.find({}))

    if category.lower() == "rebirths":
        all_users = [u for u in all_users if u.get("rebirths", 0) > 0]
        if not all_users:
            await ctx.send("🌟 Nobody has rebirths yet!")
            return
        all_users.sort(key=lambda u: u.get("rebirths", 0), reverse=True)
        top = all_users[:10]
        lines = ["🌟 **REBIRTH LEADERBOARD — TOP 10**\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, u in enumerate(top):
            member = ctx.guild.get_member(int(u["_id"]))
            name = member.display_name if member else "Unknown"
            medal = medals[i] if i < 3 else f"**#{i+1}**"
            lines.append(f"{medal} {name} — **{u.get('rebirths', 0)}** rebirths")
        await ctx.send("\n".join(lines))
    else:
        all_users = [u for u in all_users if u.get("best_roll")]
        if not all_users:
            await ctx.send("🏆 No one has rolled anything yet!")
            return
        all_users.sort(key=lambda u: ROLES.index(u["best_roll"]), reverse=True)
        top = all_users[:10]
        lines = ["🏆 **LUCK LEADERBOARD — TOP 10**\n"]
        medals = ["🥇", "🥈", "🥉"]
        for i, u in enumerate(top):
            member = ctx.guild.get_member(int(u["_id"]))
            name = member.display_name if member else "Unknown"
            best = u["best_roll"]
            chance = ROLE_DISPLAY_CHANCES[best]
            medal = medals[i] if i < 3 else f"**#{i+1}**"
            lines.append(f"{medal} {name} — **{best}** *(chance: {chance})*")
        await ctx.send("\n".join(lines))

bot.run(TOKEN)
