from discord.ext import commands
import discord

from builder import make_maze
import random
import math

class Map:
    def rand(self):
        direction = random.randint(0, 3)
        if direction == 0:
            x = random.randint(1, len(self.map) - 2)
            y = 0
        elif direction == 1:
            x = 0
            y = random.randint(1, len(self.map[0]) - 2)
        elif direction == 2:
            x = random.randint(1, len(self.map) - 2)
            y = len(self.map[0]) - 1
        else:
            x = len(self.map) - 1
            y = random.randint(1, len(self.map[0]) - 2)

        if (x == 0 and self.map[x+1][y] != " ") or (y == 0 and self.map[x][y+1] != " ") or (x == len(self.map) - 1 and self.map[x-1][y] != " ") or (y == len(self.map[0]) - 1 and self.map[x][y-1]) :
            return self.rand()

        return [x,y]

    def __init__(self, map):
        self.map = map
        self.player = [0, 0]
        self.won = False


        x,y = self.rand()
        self.player = [x, y]
        self.map[x] = self.map[x][:y] + "🐒" + self.map[x][y+1:]

        while x == self.player[0] and y == self.player[1] or self.map[x][y] == " ":
            x, y = self.rand()

        self.map[x] = self.map[x][:y] + "🏁" + self.map[x][y+1:]


    def __str__(self):
        return "\n".join(self.map)

    def move(self,x,y):
        try:
            if self.map[x][y] != " "  and self.map[x][y] != "🏁":
                return
        except IndexError:
            return

        if self.map[x][y] == "🏁":
            self.won = True

        self.map[self.player[0]] = self.map[self.player[0]].replace("🐒", " ")
        self.player = [x, y]
        self.map[x] = self.map[x][:y] + "🐒" + self.map[x][y+1:]


games = {}

bot = commands.Bot(command_prefix=commands.when_mentioned_or("+"))

def draw(game, status):
    blank = str(discord.utils.get(bot.emojis, name="v_"))
    message = ""
    for i in range(game.player[0] - 5, game.player[0] + 5):
        for j in range(game.player[1] - 5, game.player[1] + 5):
            if i < 0 or j < 0 or i >= len(game.map) or j >= len(game.map[i]):
                message += blank
                continue

            message += game.map[i][j] if game.map[i][j] != " " else blank

        message += "\n"

    return message + status

@bot.command(name = "maze")
async def start(ctx, size = "3x3", color = "white"):
    b = "⬜" if color.lower() == "white" else "⬛"
    w,h = size.lower().split("x")
    if int(w) < 3 or int(h) < 3 or int(w) > 35 or int(h) > 35:
        await ctx.send("Invalid size: range(3x3 - 35x35)")
        return

    try:
        if games.get(ctx.author.id) is not None:
            await games[ctx.author.id][1].delete()
    except Exception:
        pass

    game = Map(make_maze(int(w),int(h)).replace("+", b).replace("-", b).replace("|", b).split("\n")[:-2])
    message = draw(game, f"\nOwner: {ctx.author.name}\nStatus: PLAYING")
    msg = await ctx.send(message)

    games[ctx.author.id] = (game, msg)

    await msg.add_reaction("⬅️")
    await msg.add_reaction("⬆️")
    await msg.add_reaction("⬇️")
    await msg.add_reaction("➡️")

    await msg.add_reaction("🛑")

@bot.event
async def on_reaction_add(reaction, user):
    try:
        game = games[user.id][0]
    except KeyError:
        return

    if str(reaction) == "⬅️":
        game.move(game.player[0], game.player[1] - 1)

    if str(reaction) == "⬆️":
        game.move(game.player[0] - 1, game.player[1])

    if str(reaction) == "⬇️":
        game.move(game.player[0] + 1, game.player[1])

    if str(reaction) == "➡️":
        game.move(game.player[0], game.player[1] + 1)

    await games[user.id][1].remove_reaction(str(reaction), user)
    if str(reaction) == "🛑":
        await games[user.id][1].delete()
        del games[user.id]
        return

    if game.won:
        await games[user.id][1].edit(content=draw(game, f"\nOwner: {user.name}\nStatus: WON"))
        del games[user.id]
    else:
        await games[user.id][1].edit(content=draw(game, f"\nOwner: {user.name}\nStatus: PLAYING"))


bot.run('-')



