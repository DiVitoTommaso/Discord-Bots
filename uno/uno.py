import asyncio

from discord.ext import commands

import random

from unodrawer import drawTable, drawHand, init
import unoloader
from unoloader import Game

cards = ()
privateCards = ()

games = {}
players = {}

queue = {}

bot = commands.Bot(command_prefix=commands.when_mentioned_or("+"))


async def play(pls):
    cardsCopy = list(cards)
    startCard = cardsCopy.pop()

    hands = {}
    for p in pls:  # create random hands for each player
        hand = []
        for _ in range(7):
            hand.append(cardsCopy.pop())

        hands[p] = hand

    game = Game(hands, cardsCopy, privateCards, startCard, redraw)  # create game
    table = drawTable(game, players)  # turn game into a message

    await firstDraw(game, pls, table)

    await game.start()


async def firstDraw(game, pls, table):
    for p in pls:
        if p in Game.BOTS:  # if player is a bot skip
            continue

        user = await bot.fetch_user(p)
        games[p] = [game]

        for line in table:
            games[p].append(await user.send(line))  # send all lines of the table

        # write player hand
        games[p].insert(1, await user.send(drawHand(game, p)))


async def apply(ctx, index, color):
    id = ctx.author.id
    game = games[id][0]  # get game where the players is

    index = index % len(game.getHand())

    if game.playerId() == id:  # check if it's teh turn of the player which edited/sent the message
        card = game.cardFromIndex(index)  # get cards from hand by reaction string

        if card.color == "Jolly":  # if it's jolly ask color then set it as card
            if not color:
                await sendAndDel(ctx, "To play a jolly you must specify a color. Ex: +play 0 yellow")
                return

            card = game.privateCardFromColor(card, color[0].upper() + color[1:].lower())  # get the colored jolly card

        if not game.canBeSet(card):  # check if card can be set
            await sendAndDel(ctx, "That card can't be played!")
            return
        else:
            await game.set(card)  # set the card. if it's not a jolly and if the card is illegal notify the player

    else:
        await sendAndDel(ctx, "It's not your turn")


@bot.event
async def on_message_edit(before, after):
    await bot.process_commands(after)


async def redraw(game):
    # get old table messages

    for p in game.players:
        if p in game.BOTS:
            continue

        oldTableMsgs = games[p][2:]
        newTable = drawTable(game, players, default=False)

        await games[p][1].edit(content=drawHand(game, p))

        # update them with the new table
        for line in range(1, len(newTable)):
            if line == 4:
                continue

            await oldTableMsgs[line].edit(content=newTable[line])

        if game.end:
            try:
                del games[p]
                del players[p]
            except KeyError:
                pass


async def sendAndDel(ctx, s):
    # send a message for 5s and delete it to avoid spam during game
    msg = await ctx.author.send(s)
    await asyncio.sleep(5)
    await msg.delete()


@bot.command(name="play", aliases=["set", "use"])
async def useCard(ctx, index="auto", color=""):
    id = ctx.author.id
    if games.get(id) is None:  # if player is not in game ignore anything
        await sendAndDel(ctx, "You are not in game!")

    if index.isdecimal():
        await apply(ctx, int(index) - 1, color)  # apply the played card
    elif index == "auto":  # if no index has passed play automatically a valid move (card or draw)
        game = games[id][0]
        hand = game.getHand()

        for i in range(len(hand)):
            if game.canBeSet(hand[i]):
                if hand[i].color == "Jolly":
                    for c in hand:
                        if c.color != "Jolly":
                            color = c.color
                            break
                else:
                    random.choice(Game.COLORS)
                    
                await apply(ctx, i, color)  # pick a random color in case the card is a jolly
                return

        await drawCard(ctx)
    else:
        await sendAndDel(ctx, "Invalid card index!")  # notify the use if it's not a valid index


@bot.on_error
async def on_error(ctx, e):
    await sendAndDel(ctx, f"An error occurred {str(e)}. Please try again in 10s")


@bot.command(name="quit")
async def exitGame(ctx):
    id = ctx.author.id
    left = ctx.author.name
    if games.get(id) is None:  # check if player is in game
        await sendAndDel(ctx, "You are not in game!")
        return

    game = games[id][0]

    game.effect_msg = players[id]["name"] + " left the game"  # communicate that the player left the game
    botsCount = len([p for p in game.players if p in Game.BOTS])

    if botsCount == 3:  # if there are already 3 bots close game because there are no more players in game (only bots)
        game.effect_msg = "All players left the game."
        game.end = True
        await redraw(game)
        return

    isCurrentPlayer = game.playerId() == id

    Bot = Game.BOTS[botsCount]  # replace the player with a bot
    game.hands[Bot] = game.hands[id]
    game.players[game.players.index(id)] = Bot

    # update only the names (replace the player name who left with a bot name)
    for p in game.players:
        if p in game.BOTS:
            continue
        oldTableMsgs = games[p][2:]
        newTable = drawTable(game, players, default=False)
        await oldTableMsgs[0].edit(content=newTable[0])
        await oldTableMsgs[4].edit(content=newTable[4])

    for p in game.players:  # notify every one that the player left the game
        if p not in Game.BOTS:
            ctx.author = await bot.fetch_user(p)
            await sendAndDel(ctx, f"{left} left the game")

    try:
        del games[id]  # delete the player
        del players[id]
    except KeyError:
        pass

    await ctx.author.send("You left the game")  # notify the player everything went well

    if isCurrentPlayer:  # check if it's the turn of the left player
        await game.runBot()  # if yes run the bot engine


@bot.command(name="uno")
async def helpUNO(ctx):
    # help command
    await ctx.author.send("**List commands**\n+host <code> <bots number>\n"
                          "**Create a room of 4 players with the given code with the specified number of bots."
                          " If it doesn't already exists**\n+join <code>\n"
                          "**Join the room represented by the given code**\n+leave\n**Leave the current room joined**\n"
                          "+quit\n**Exit the current game (you will be replaced by a bot)**\n"
                          "+play <index>\n**Play the card from your hand at the given index (index starts from 1)\n"
                          "If no valid index has been detected. "
                          "The first valid card will be played (if possible) else a card will be drown\n**"
                          "+draw\n**Draw a card from the deck and skip the turn**")


@bot.command(name="leave")
async def dequeue(ctx):
    if players.get(ctx.author.id) is None:  # if user is not in queue ignore
        await sendAndDel(ctx, "You are not in any room!")
        return

    code = players[ctx.author.id]["code"]
    if players.get(ctx.author.id) is not None and ctx.author.id not in queue[code]:
        # check if it's not in the queue but it's playing
        await sendAndDel(ctx, "You are already playing!")
        return

    await ctx.author.send(f"You left the room!")  # if it was waiting remove it
    queue[code].remove(ctx.author.id)

    for p in queue[code]:  # communicate that the user left the room
        await write(p, f"{ctx.author.name} left the room. Players: {len(queue[code])}/4")

    if len(queue[code]) == 0 or set(queue[code]).issubset(set(Game.BOTS)):  # if every player left the room delete it
        del queue[code]

    del players[ctx.author.id]  # delete it from the players


@bot.command(name="host")
async def host(ctx, code, bots="0"):
    if not bots.isdecimal():
        await sendAndDel(ctx, "Bots number must be in range(0-3)!")
        return

    bots = int(bots)

    if bots < 0 or bots > 3:
        await sendAndDel(ctx, "Bots number must be in range(0-3)!")
        return

    if queue.get(code) is None:  # check if room already exists
        queue[code] = []
        createBots(code, bots)
        await enqueue(ctx, code)  # initialize the room then join it
    else:
        await sendAndDel(ctx, "This code already exists!")


@bot.command(name="draw")
async def drawCard(ctx):
    if games.get(ctx.author.id) is None:  # check if player is in game
        await sendAndDel(ctx, "You are not in game!")
        return

    game = games[ctx.author.id][0]
    if game.playerId() == ctx.author.id:  # check if it's his turn
        await game.draw(1, check=True)
    else:
        await sendAndDel(ctx, "It's not your turn!")
        return


@bot.command(name="join")
async def enqueue(ctx, code):
    if queue.get(code) is None:  # check if room already exists
        await sendAndDel(ctx, "This room code doesn't exists")
        return

    if players.get(ctx.author.id) is not None:  # check if player is already in a game
        await sendAndDel(ctx, "You are already in a game!")
        return

    players[ctx.author.id] = {"code": code, "name": ctx.author.name}  # add the player to the players collection
    queue[code].append(ctx.author.id)  # add it to the queue for that code

    for p in queue[code]:  # notify every one that the user has joined their room
        await write(p, f"{ctx.author.name} joined the room. Players: {len(queue[code])}/4")

    if len(queue[code]) == 4:  # if the queue is full then start the game
        for p in queue[code]:
            await write(p, "Starting...")

        await play(queue[code])  # start the game

        del queue[code]


@bot.event
async def on_ready():
    global cards, privateCards
    cards, privateCards = unoloader.load(bot)  # load cards
    init(bot)


async def write(p, msg):
    if p in Game.BOTS:  # skip if it's a bot
        return

    user = await bot.fetch_user(p)
    await user.send(msg)


def createBots(code, num):
    for i in range(num):
        queue[code].append(Game.BOTS[i])


bot.run('-')
