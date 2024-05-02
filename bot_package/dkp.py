from discord.ext import commands, tasks
import discord
from typing import Union
import calendar
import psycopg2
import datetime
import requests

class dekape(commands.Cog):
    user_lvls = {}
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.classes_colors = {
                "death knight": "#C41E3A",
                "demon hunter": "#A330C9",
                "druid": "#FF7C0A",
                "evoker": "#33937F",
                "hunter": "#AAD372",
                "mage": "#3FC7EB",
                "monk": "#00FF98",
                "paladin": "#F48CBA",
                "priest": "#FFFFFF",
                "rogue": "#FFF468",
                "shaman": "#0070DD",
                "warlock": "#8788EE",
                "warrior": "#C69B6D"
            }
        self.update_levels.start()
        
    def delete_user(self, discord_user_id):
        query = f"""SELECT id FROM players
                WHERE discord_user_id = '{discord_user_id}' or character = '{discord_user_id}';"""
        data = self.wpisz_single_sql(query, 1, None)
        if data:
            id = data[0][0]
            query = f"""DELETE FROM awards
                        WHERE character_id = '{id}'
                        RETURNING id;"""
            self.wpisz_single_sql(query, 1, None)
            query = f"""DELETE FROM spent
                        WHERE character_id = '{id}'
                        RETURNING id;"""
            self.wpisz_single_sql(query, 1, None)
            query = f"""DELETE FROM players
                        WHERE id = '{id}'
                        RETURNING id;"""
            self.wpisz_single_sql(query, 1, None)
            return True
        else:
            return False
        
    def update_current_dkp(self, character_id: int, points: float):
        query = f"""SELECT current_dkp FROM players
                    WHERE id = '{character_id}'"""
        data = self.wpisz_single_sql(query, 1, None)
        current_dkp = data[0][0] + points
        query = f"""UPDATE players
                    SET current_dkp = {current_dkp}
                    WHERE id = {character_id} RETURNING id;"""
        self.wpisz_single_sql(query, 1, None)

    def wpisz_single_sql(self, query: str, mode: int, *data):
        host = "51.77.58.59"
        database = "boosty"
        username = "cin"
        password = "postgre"
        cnxn = psycopg2.connect(host=host, database=database, user=username, password=password)
        cursor = cnxn.cursor()
        if mode == 1:
            cursor.execute(query)
            cnxn.commit()
            fetched = cursor.fetchall()
        elif mode in [2, 3]:
            members_in_database = data[0]
            friendlies_boss_kills = data[1]
            quantity = data[2]
            note = data[3]
            date = data[4]
            awarded_members = 0
            if mode == 2:
                awarded_by = data[5]
                for killer, kills_number in friendlies_boss_kills.items():
                    if killer in members_in_database.keys():
                        character_id = members_in_database[killer]
                        points = quantity * kills_number
                        query = f"""INSERT INTO awards (character_id, awarded_dkp, note, date, awarded_by)
                                    VALUES ('{character_id}', '{points}', '{note}', '{date}', '{awarded_by}');"""
                        cursor.execute(query)
                        self.update_current_dkp(character_id, points)
                        awarded_members += 1
            if mode == 3:
                for killer, kills_number in friendlies_boss_kills.items():
                    if killer in members_in_database.keys():
                        character_id = members_in_database[killer]
                        points = quantity * kills_number
                        query = f"""INSERT INTO spent (character_id, spent_dkp, spent_on, date)
                                    VALUES ('{character_id}', '{points}', '{note}', '{date}');"""
                        cursor.execute(query)
                        self.update_current_dkp(character_id, points)
                        awarded_members += 1
            cnxn.commit()
        elif mode == 4:
            members_to_update = data[0]
            for id, levelxp in members_to_update.items():
                query = f"""UPDATE players
                            SET level = {levelxp[0]}, 
                                xp = {levelxp[1]}
                            WHERE discord_user_id = '{id}';"""
                cursor.execute(query)
            cnxn.commit()
        cnxn.close()
        if mode == 1:
            return fetched
        elif mode in [2, 3]:
            return True, awarded_members
        
    def add_member(self, character_nick, character_class, discord_user_id):
        query = f"""INSERT INTO players (character, class, discord_user_id, level, xp)
                VALUES ('{character_nick.capitalize()}', '{character_class}', '{discord_user_id}', '1', '0') RETURNING id;"""
        character_id = self.wpisz_single_sql(query, 1, None)
        zero = 0
        note = ""
        date = datetime.date.today()
        awarded_by = ""
        spent_on = ""
        query = f"""INSERT INTO awards (character_id, awarded_dkp, note, date, awarded_by)
                    VALUES ('{character_id[0][0]}', '{zero}', '{note}', '{date}', '{awarded_by}') RETURNING id"""
        self.wpisz_single_sql(query, 1, None)
        query = f"""INSERT INTO spent (character_id, spent_dkp, spent_on, date)
                    VALUES ('{character_id[0][0]}', '{zero}', '{spent_on}', '{date}') RETURNING id"""
        self.wpisz_single_sql(query, 1, None)
        self.user_lvls[str(discord_user_id)] = (1, 0)

    def already_in_database(self, discord_user_id):
        query = f"""SELECT * FROM players
            WHERE players.discord_user_id = '{discord_user_id}'"""
        data = self.wpisz_single_sql(query, 1, None)
        if data:
            return True
        else:
            return False
        
    def any_none(self, *data):
        for data_item in data:
            if data_item is None:
                return True
        return False
    
    @tasks.loop(hours=24)
    async def update_levels(self):
        self.wpisz_single_sql(None, 4, dekape.user_lvls)
        
    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        discord_user_id = payload.user.id
        self.delete_user(discord_user_id)

    @commands.command()
    async def dodaj(self, ctx: commands.Context, member: discord.Member = None, character_nick: str = None, *character_class_set: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You don't have permissions to do that.")
            return
        if member is None or character_nick is None or len(character_class_set) == 0:
            await ctx.send("One or more required parameters are missing")
            return
        character_class = ' '.join(character_class_set).lower()
        if character_class not in self.classes_colors.keys():
            await ctx.send("Provide a correct class")
            return
        discord_user_id = member.id
        if self.already_in_database(discord_user_id):
            await ctx.send("Member already in database")
            return
        self.add_member(character_nick, character_class, discord_user_id)
        await ctx.send("Member added")

    @commands.command()
    async def addself(self, ctx: commands.Context, character_nick: str = None, *character_class_set: str):
        if character_nick is None or len(character_class_set) == 0:
            await ctx.send("One or more required parameters are missing")
            return
        character_class = ' '.join(character_class_set).lower()
        if character_class not in self.classes_colors.keys():
            await ctx.send("Provide a correct class")
            return
        discord_user_id = ctx.author.id
        if self.already_in_database(discord_user_id):
            await ctx.send("You are already in database")
            return
        self.add_member(character_nick, character_class, discord_user_id)
        await ctx.send("Added yourself")

    @commands.command()
    async def dej(self, ctx: commands.Context, member: Union[discord.Member, discord.Role, str], quantity: float = 0, *note: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You don't have permissions to do that.")
            return
        if type(quantity) != float:
            await ctx.send("Provide a correct number")
            return
        joined_note = " ".join(note)
        date = datetime.date.today()
        members_to_award = {}
        if type(member) == discord.Member:
            members_to_award[str(member.id)] = 1
            query = f"""SELECT id, discord_user_id FROM players"""
        elif type(member) == discord.Role:
            members_to_award = {str(x.id): 1 for x in ctx.guild.members if member in x.roles}
            query = f"""SELECT id, discord_user_id FROM players"""
        else:
            members_to_award[member.capitalize()] = 1
            query = f"""SELECT id, character FROM players"""
        data = self.wpisz_single_sql(query, 1, None)
        if data:
            members_in_database = {}
            for data_item in data:
                members_in_database[data_item[1]] = data_item[0]
            wpisane, awarded_members = self.wpisz_single_sql(None, 2, members_in_database, members_to_award, quantity, joined_note, date, ctx.author.display_name)
            if wpisane:
                await ctx.send(f"Awarded DKP to {awarded_members} members")
            else:
                await ctx.send("Something went wrong...")

    @commands.command()
    async def zabierz(self, ctx: commands.Context, member: Union[discord.Member, discord.Role, str], quantity: float = 0, *note: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You don't have permissions to do that.")
            return
        if type(quantity) != float:
            await ctx.send("Provide a correct number")
            return
        joined_note = " ".join(note)
        date = datetime.date.today()
        members_to_award = {}
        if type(member) == discord.Member:
            members_to_award[str(member.id)] = 1
            query = f"""SELECT id, discord_user_id FROM players"""
        elif type(member) == discord.Role:
            members_to_award = {str(x.id): 1 for x in ctx.guild.members if member in x.roles}
            query = f"""SELECT id, discord_user_id FROM players"""
        else:
            members_to_award[member.capitalize()] = 1
            query = f"""SELECT id, character FROM players"""
        data = self.wpisz_single_sql(query, 1, None)
        if data:
            members_in_database = {}
            for data_item in data:
                members_in_database[data_item[1]] = data_item[0]
            wpisane, awarded_members = self.wpisz_single_sql(None, 3, members_in_database, members_to_award, quantity, joined_note, date, ctx.author.display_name)
            if wpisane:
                await ctx.send(f"Subtracted DKP from {awarded_members} members")
            else:
                await ctx.send("Something went wrong...")

    @commands.command()
    async def change(self, ctx: commands.Context, member: Union[discord.Member, str] = None, to_change: str = None, change_to: str = None):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You don't have permissions to do that.")
            return
        if self.any_none(member, to_change, change_to):
            await ctx.send("One or more required parameters are missing")
            return
        to_change_list = {
            "character": "character",
            "class": "class"
        }
        if to_change.lower() not in to_change_list:
            await ctx.send(f"Entry to change has to be: {', '.join(to_change_list)}")
            return
        if to_change.lower() == "class":
            if change_to.lower() not in self.classes_colors.keys():
                await ctx.send("Provide a correct class")
                return
        if type(member) == discord.Member:
            member = member.id
        query = f"""SELECT id FROM players
                    WHERE discord_user_id = '{member}' or character = '{member}';"""
        data = self.wpisz_single_sql(query, 1, None)
        if data:
            id = data[0][0]
            query = f"""UPDATE players
                        SET {to_change} = '{change_to.capitalize()}'
                        WHERE id = '{id}' RETURNING id;"""
            self.wpisz_single_sql(query, 1, None)
            await ctx.send("Member changed")
        else:
            await ctx.send("Member doesn't exist in the database")

    @commands.command()
    async def raid(self, ctx: commands.Context, log_link: str = None, quantity: float = 0, *note: str):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You don't have permissions to do that.")
            return
        start_index = log_link.find("reports/") + len("reports/")
        if start_index == 7:
            await ctx.send("Provide a correct report")
            return
        if type(quantity) != float or quantity == 0:
            await ctx.send("Provide a correct number")
            return
        end_index = log_link.find("#")
        if end_index == -1:
            end_index = len(log_link)
        api_key = "6b437017b4771cf6f1226c9421a2e10c"
        report_key = log_link[start_index:end_index]
        url = f"https://www.warcraftlogs.com:443/v1/report/fights/{report_key}?api_key={api_key}"
        response = requests.get(url=url)
        if response.status_code != 200:
            await ctx.send(f"Error retrieving data")
            return
        report_miliseconds = response.json()["start"]
        report_seconds = report_miliseconds / 1000
        report_date = datetime.datetime.fromtimestamp(report_seconds).strftime("%Y-%m-%d")
        joined_note = " ".join(note)
        fights = response.json()["fights"]
        boss_kill_ids = []
        for fight in fights:
            try:
                if fight["kill"] == True:
                    boss_kill_ids.append(fight["id"])
            except KeyError:
                continue

        boss_killers = {}

        for boss_id in boss_kill_ids:
            boss_killers[boss_id] = []

        friendlies = response.json()["friendlies"]
        for friendly in friendlies:
            try:
                if friendly["type"] != "NPC":
                    for fight in friendly["fights"]:
                        if fight["id"] in boss_killers.keys():
                            boss_killers[fight["id"]].append(friendly["name"])
            except KeyError:
                continue

        friendlies_boss_kills = {}  
        for _, v in boss_killers.items():
            for boss_killer in v:
                if boss_killer not in friendlies_boss_kills.keys():
                    friendlies_boss_kills[boss_killer] = 1
                else:
                    friendlies_boss_kills[boss_killer] += 1

        query = f"""SELECT id, character FROM players"""
        data = self.wpisz_single_sql(query, 1, None)
        if data:
            members_in_database = {}
            for data_item in data:
                members_in_database[data_item[1]] = data_item[0]
            wpisane, awarded_members = self.wpisz_single_sql(None, 2, members_in_database, friendlies_boss_kills, quantity, joined_note, report_date, ctx.author.display_name)
            if wpisane:
                await ctx.send(f"Awarded DKP to {awarded_members} members")
            else:
                await ctx.send("Something went wrong...")

    @commands.command()
    async def usun(self, ctx: commands.Context, member: Union[discord.User, str] = None):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You don't have permissions to do that.")
            return
        if member is None:
            await ctx.send("Please specify a member")
            return
        if type(member) == discord.User:
            discord_user_id = member.id
        elif member.isdigit():
            await ctx.send("Please ping a user or give user id")
            return
        else:
            discord_user_id = member
        deleted = self.delete_user(discord_user_id)
        if deleted:
            del dekape.user_lvls[str(discord_user_id)]
            await ctx.send("Member deleted")
        elif not deleted:
            await ctx.send("Member doesn't exist in the database")

    @commands.command()
    async def ranking(self, ctx: commands.Context):
        query = f"""SELECT * FROM players
                ORDER BY current_dkp DESC;"""
        data = self.wpisz_single_sql(query, 1, None)
        if not data:
            await ctx.send("Ranking jest pusty")
            return
        title = "Ranking DKP"
        hex = "#FF00FF"
        color = discord.Colour.from_str(hex)
        fields = {
            f"1 - {min(16, len(data))}": ("", True),
            f"17 - {min(32, len(data))}": ("", True),
            f"33 - {min(48, len(data))}": ("", True)
        }
        embed = discord.Embed(title=title, color=color)
        field_count = (len(data) // 16) + 1
        for i, (k, v) in enumerate(fields.items()):
            if i >= field_count:
                break
            embed.add_field(name=k, value=v[0], inline=v[1])
        for i, data_part in enumerate(data):
            nick = data_part[1]
            current_dkp = data_part[3]
            if i <= 16:
                embed.set_field_at(0, name=f"1 - {min(16, len(data))}", value=embed.fields[0].value + f"`{current_dkp} DKP` {nick}\n", inline=True)
            elif i <= 32:
                embed.set_field_at(1, name=f"17 - {min(32, len(data))}", value=embed.fields[1].value + f"`{current_dkp} DKP` {nick}\n", inline=True)
            elif i <= 48:
                embed.set_field_at(2, name=f"33 - {min(32, len(data))}", value=embed.fields[2].value + f"`{current_dkp} DKP` {nick}\n", inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def profil(self, ctx: commands.Context, arg: Union[discord.Member, str] = None):
        if arg is None:
            arg = ctx.author.id
            url = ctx.author.display_avatar
        if type(arg) == discord.Member:
            url = arg.display_avatar
            arg = arg.id
        query = f"""SELECT * FROM players
                LEFT JOIN awards ON players.id = awards.character_id
                WHERE players.character = '{arg}' OR players.discord_user_id = '{arg}'
                ORDER BY awards.id DESC;"""
        data = self.wpisz_single_sql(query, 1, None)
        if not data:
            await ctx.send("Member doesn't exist in the database")
            return
        inner_data = data[0]
        character_nick = inner_data[1]
        character_class = inner_data[2]
        current_dkp = inner_data[3]
        lifetime_gained = 0
        award_date = inner_data[11]
        award_day = award_date.day
        award_month = award_date.month
        award_month_name = calendar.month_abbr[award_month]
        last_awarded_dkp = inner_data[9]
        note = inner_data[10]
        awarded_by = inner_data[12]
        for entrance in data:
            lifetime_gained += entrance[9]
        query = f"""SELECT * FROM players
                LEFT JOIN spent ON players.id = spent.character_id
                WHERE players.character = '{arg}' OR players.discord_user_id = '{arg}'
                ORDER BY spent.id DESC;"""
        data = self.wpisz_single_sql(query, 1, None)
        inner_data = data[0]
        spent_date = inner_data[11]
        spent_day = spent_date.day
        spent_month = spent_date.month
        spend_month_name = calendar.month_abbr[spent_month]
        last_spent_dkp = inner_data[9]
        last_spent_on = inner_data[10]
        lifetime_spent = 0
        for entrance in data:
            lifetime_spent += entrance[9]
        f_lifetime_gained = float("{:.1f}".format(lifetime_gained))
        f_lifetime_spent = float("{:.1f}".format(lifetime_spent))
        f_last_awarded_dkp = float("{:.1f}".format(last_awarded_dkp))
        f_last_spent_dkp = float("{:.1f}".format(last_spent_dkp))
        f_current_dkp = float("{:.1f}".format(current_dkp))
        title = "Profil DKP"
        desc = f"**{character_nick.capitalize()}**\n{character_class.capitalize()}"
        hex = self.classes_colors[character_class.lower()]
        color = discord.Colour.from_str(hex)
        fields = {
            "Current:": (f"`{f_current_dkp} DKP`", False),
            "Lifetime gained:": (f"`{f_lifetime_gained} DKP`", True),
            "Lifetime spent:": (f"`{f_lifetime_spent} DKP`", True),
            "Last DKP award:": (f"`{award_month_name} {award_day}` - `{f_last_awarded_dkp} DKP` - {note} by {awarded_by}", False),
            "Last DKP spent:": (f"`{spend_month_name} {spent_day}` - `{f_last_spent_dkp} DKP` - {last_spent_on}", False)
        }
        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_thumbnail(url=url)
        for k, v in fields.items():
            embed.add_field(name=k, value=v[0], inline=v[1])
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(dekape(bot))