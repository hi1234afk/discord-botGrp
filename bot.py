import discord
from discord.ext import commands
import json
import os

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

REQUIRED_INVITES = 2
INVITE_FILE = "invite_counts.json"
SETTINGS_FILE = "settings.json"

def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return default
    return default

invite_counts = load_json(INVITE_FILE, {})
settings = load_json(SETTINGS_FILE, {
    "enabled": True,
    "role": "Giveaway",
    "log_channel": None
})

def save_data():
    with open(INVITE_FILE, "w") as f:
        json.dump(invite_counts, f)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")
    bot.invites = {}
    for guild in bot.guilds:
        bot.invites[guild.id] = await guild.invites()

@bot.event
async def on_member_join(member):
    if not settings["enabled"]:
        return
    guild = member.guild
    log_channel = None
    if settings["log_channel"]:
        log_channel = guild.get_channel(settings["log_channel"])
    new_invites = await guild.invites()
    old_invites = bot.invites[guild.id]
    inviter = None
    for invite in new_invites:
        for old in old_invites:
            if invite.code == old.code and invite.uses > old.uses:
                inviter = guild.get_member(invite.inviter.id)
    bot.invites[guild.id] = new_invites
    if inviter is None:
        print("Unbekannter Invite – ignoriert")
        return
    user_id = str(inviter.id)
    invite_counts[user_id] = invite_counts.get(user_id, 0) + 1
    role = discord.utils.get(guild.roles, name=settings["role"])
    role_given = False
    if invite_counts[user_id] >= REQUIRED_INVITES:
        if role:
            try:
                await inviter.add_roles(role)
                role_given = True
            except Exception as e:
                print("❌ Fehler beim Rollen geben:", e)
    save_data()
    if log_channel:
        embed = discord.Embed(title="📥 Neuer Join!", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Member", value=f"{member.mention}", inline=True)
        embed.add_field(name="📨 Eingeladen von", value=f"{inviter.mention}", inline=True)
        embed.add_field(name="📊 Invites", value=f"{invite_counts[user_id]}", inline=True)
        embed.add_field(name="🎭 Rolle erhalten", value="✅ Ja" if role_given else "❌ Nein", inline=True)
        embed.set_footer(text="Invite-System")
        await log_channel.send(embed=embed)

@bot.command()
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    count = invite_counts.get(str(member.id), 0)
    await ctx.send(f"{member.name} hat {count} Invites!")

@bot.command()
@commands.has_permissions(administrator=True)
async def addinvites(ctx, member: discord.Member, amount: int):
    invite_counts[str(member.id)] = invite_counts.get(str(member.id), 0) + amount
    role = discord.utils.get(ctx.guild.roles, name=settings["role"])
    if invite_counts[str(member.id)] >= REQUIRED_INVITES:
        if role:
            try:
                await member.add_roles(role)
                await ctx.send(f"🎉 {member.name} hat die Rolle bekommen!")
            except Exception as e:
                await ctx.send(f"❌ Fehler: {e}")
    save_data()
    await ctx.send(f"✅ {amount} Invites hinzugefügt für {member.name}")

@bot.command()
@commands.has_permissions(administrator=True)
async def removeinvites(ctx, member: discord.Member, amount: int):
    invite_counts[str(member.id)] = max(0, invite_counts.get(str(member.id), 0) - amount)
    role = discord.utils.get(ctx.guild.roles, name=settings["role"])
    if invite_counts[str(member.id)] < REQUIRED_INVITES:
        if role in member.roles:
            await member.remove_roles(role)
    save_data()
    await ctx.send(f"❌ {amount} Invites entfernt von {member.name}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setrole(ctx, *, role_name):
    settings["role"] = role_name
    save_data()
    await ctx.send(f"🎭 Rolle geändert zu: {role_name}")

@bot.command()
@commands.has_permissions(administrator=True)
async def stop(ctx):
    settings["enabled"] = False
    save_data()
    await ctx.send("⛔ Invite-System gestoppt")

@bot.command()
@commands.has_permissions(administrator=True)
async def start(ctx):
    settings["enabled"] = True
    save_data()
    await ctx.send("✅ Invite-System gestartet")

@bot.command()
@commands.has_permissions(administrator=True)
async def setlogchannel(ctx):
    settings["log_channel"] = ctx.channel.id
    save_data()
    await ctx.send(f"✅ Log-Channel gesetzt auf: {ctx.channel.mention}")

token = os.environ.get("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN nicht gesetzt!")
bot.run(token)
