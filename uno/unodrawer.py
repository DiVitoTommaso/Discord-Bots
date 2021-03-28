import discord
import unoloader

back = ""
void = ""


def playerFromIndex(playersDict, game, i):
    if game.isBotIndex(i):
        return "Bot " + str(- game.playerId(i))
    return playersDict[game.playerId(i)]["name"]


def drawTable(game, playersDict, default=True):
    if default:  # it's first draw ? yes => UNO played else (game.prev) played
        player = "Loading..."
    else:
        player = playerFromIndex(playersDict, game, game.prevPlayerIndex)

    space = " " * 48

    # turn game into multiple messages
    table = [f'**{playerFromIndex(playersDict, game, 0)}{space}{playerFromIndex(playersDict, game, 1)}**',  # skip 0
             f'{game.intToEmoji(len(game.getHand(0)))}{back}{void * (3 - game.dsEmojiLen(0))}' +
             f'{back}{game.intToEmoji(len(game.getHand(1)))}',
             f'{void * 2}{str(game.card)}{back if len(game.deck) > 0 else ":x:"}{void * 2}',
             f'{game.intToEmoji(len(game.getHand(2)))}{back}{void * (3 - game.dsEmojiLen(2))}' +
             f'{back}{game.intToEmoji(len(game.getHand(3)))}',
             f'**{playerFromIndex(playersDict, game, 2)}{space}{playerFromIndex(playersDict, game, 3)}**\n',  # skip 4
             f"News: **{player}** Played: **{game.effect_msg}** {' **GAME END**' if game.end else ''}\n" +
             f"Rotation: {'🔁' if game.clockwise else '🔄'}\n" +
             f'Turn: **{playerFromIndex(playersDict, game, -1)}**\n' +
             f"{void * 3}\n**YOUR CARDS:**"
             ]

    return table


def drawHand(game, p):
    # turn the hand of the player into a message
    hand = ""

    for card in game.hands[p]:  # convert hand to a message
        hand += str(card)

    return hand if hand else ":x:"


def init(bot):
    # load the cards
    global void, back
    void = str(discord.utils.get(bot.emojis, name="v_"))
    _, privateCards = unoloader.load(bot)
    back = privateCards[-1]
