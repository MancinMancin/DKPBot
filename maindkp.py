import discord
from discord.ext import commands
from config import token
from bot_package.dkp import dekape

bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())
bot.remove_command("help")

ext = ["dkp", "levels"]

@bot.event
async def on_ready():
    for extension in ext:
        await bot.load_extension(f"bot_package.{extension}")
    query = f"""SELECT discord_user_id, level, xp from players;"""
    data = dekape(bot).wpisz_single_sql(query, 1, None)
    if data:
        for user in data:
            user_id = user[0]
            level = user[1]
            xp = user[2]
            dekape.user_lvls[user_id] = (level, xp)
    print(f"Logged in as {bot.user}")

@bot.command()
@commands.is_owner()
async def load(ctx, extension):
    try:
        await bot.load_extension(f"bot_package.{extension}")
        desc = f"{extension} successfully loaded"
    except (commands.ExtensionNotFound, commands.ExtensionAlreadyLoaded) as e:
        desc = f"{extension} couldn't load\n\nError: {e}"
    finally:
        embed = discord.Embed(title='Load', description=desc, color=0xff00c8)
        await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def reload(ctx, extension):
    try:
        await bot.reload_extension(f"bot_package.{extension}")
        desc = f"{extension} successfully reloaded"
    except commands.ExtensionNotLoaded as e:
        desc = f"{extension} couldn't reload\n\nError: {e}"
    finally:
        embed = discord.Embed(title='Reload', description=desc, color=0xff00c8)
        await ctx.send(embed=embed)

bot.run(token)