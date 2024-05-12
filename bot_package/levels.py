from discord.ext import commands
from bot_package.dkp import dekape
import datetime
import discord

class levels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def lvl_up(self, xp, character_id):
        if xp >= 50:
            query = f"""SELECT id from players
                        WHERE discord_user_id = '{character_id}'"""
            id = dekape(self.bot).wpisz_single_sql(query, 1, None)[0][0]
            date = datetime.date.today()
            query = f"""INSERT INTO awards (character_id, awarded_dkp, note, date, awarded_by)
                        VALUES ('{id}', '1', 'Level up!', '{date}', 'Level up') RETURNING id;"""
            dekape().wpisz_single_sql(query, 1, None)
            dekape().update_current_dkp(id, 1)
            return True
        else:
            return False
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if str(message.author.id) in dekape.user_lvls.keys():
            level = dekape.user_lvls[str(message.author.id)][0]
            xp = dekape.user_lvls[str(message.author.id)][1]
            xp += 1
            if self.lvl_up(xp, str(message.author.id)):
                level += 1
                xp = 0
                await message.channel.send(f"{message.author.mention} is now lvl {level}!")
            dekape.user_lvls[str(message.author.id)] = (level, xp)

    @commands.command()
    async def help(self, ctx: commands.Context, arg: str = None):
        if arg != None:
            if arg.lower() == "admin":
                if not ctx.author.guild_permissions.administrator:
                    await ctx.send("You don't have permissions to do that.")
                    return
                fields = {
                    "/usun <user ping or user id>": ("Deletes the user from the database", False),
                    "/dodaj <user ping> <character nick> <character class>": ("Adds the user to the database.", False),
                    "/dej <user ping or role ping or character nick> <quantity> <note (optional)>": ("Awards pinged user or every user with pinged role the given amount of DKP", False),
                    "/zabierz <user ping or role ping or character nick> <quantity> <note (optional)>": ("Subtracts pinged user or every user with pinged role the given amount of DKP", False),
                    "/logi <log link> <quantity> <note (optional)>": ("Awards users killing the bosses with given DKP per boss kill", False),
                    "/change <user ping or character nick> <\"character\" or \"class\"> <new character nick or new class>": ("", False)
                }
        else:
            fields = {
                "/ranking": ("Shows ranking", False),
                "/profil <user ping or character nick (optional)>": ("Shows your or chosen user profile.", False),
                "/addself <character nick> <character class>": ("Add yourself to the database.", False),
            }
        color = discord.Colour.brand_red()
        title = "Help"
        embed = discord.Embed(title=title, color=color)
        for k, v in fields.items():
            embed.add_field(name=k, value=v[0], inline=v[1])
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(levels(bot))