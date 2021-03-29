import discord
import random
import asyncio

clockNext = {
    0: 1,
    1: 3,
    3: 2,
    2: 0
}

antiClockNext = {
    0: 2,
    2: 3,
    3: 1,
    1: 0,

}


# a timer class to avoid game starvation not implemented for the moment
class Timer:
    def __init__(self, game):
        self.time = 20
        self.game = game

    async def runTurnTimer(self):
        while not self.game.end:  # is game is active

            if self.time == 0:  # if time is 0 turn time ahs ended
                self.time = 20  # reset the timer

                # if player has already drown skip only else draw and skip
                if self.game.skippable.get(self.game.playerId()) is not None:
                    del self.game.skippable[self.game.playerId()]
                    await self.game.draw(0, afk=True, skip=True)
                else:
                    await self.game.draw(1, afk=True, skip=True)

            self.time -= 1  # decrease the timer async
            await asyncio.sleep(1)

    async def runGameTimer(self):
        await asyncio.sleep(1800)  # max game time 30m
        self.game.end = True
        self.game.effect_msg = "Max game time exceeded. Stopping game... "
        await self.game.redraw(self.game)

    def resetTurnTimer(self):
        self.time = 20


# class used to represent a UNO Card
class Card:
    def __init__(self, emoji, color: str = None, value: int = None, effect: str = None):
        self.emoji = str(emoji)
        self.color = color
        self.value = value
        self.effect = effect

    def __str__(self):
        return self.emoji


def sortCards(c):
    if c.color == "Jolly":
        return "z", 100
    return c.color, c.value


class Game:
    # bot id
    BOTS = (-1, -2, -3)
    COLORS = ("Yellow", "Red", "Blue", "Green")

    def __init__(self, hands: dict, deck: list, privateCards, start: Card, botRedraw, skippable: dict):
        deck.append(start)

        self.redraw = botRedraw
        self.skippable = skippable

        self.privateCards = privateCards
        self.deck = deck
        self.card = start
        self.hands = hands

        self.clockwise = True
        self.players = list(hands.keys())
        random.shuffle(self.players)

        self.winners = []

        for player in self.players:  # sort each hand
            hands[player].sort(key=sortCards)

        self.end = False

        self.currentPlayerIndex = 0
        self.prevPlayerIndex = -1

        if start.value == -1:  # if starting card is a jolly pick a random color
            color = random.choice(Game.COLORS)
            jolly = self.privateCardFromColor(start, color)
            self.card = jolly

        self.effect_msg = "Loading..."

        self.timer = Timer(self)

    async def start(self):
        self.effect_msg = await self.apply(self.card)
        await self.timer.runTurnTimer()
        await self

    def playerId(self, i=-1) -> int:
        # return the player associated to that index. if not index is passed return the current player
        if i == -1:
            return self.players[self.currentPlayerIndex]
        return self.players[i]

    def cardFromIndex(self, i):
        # get card in hand of the current player from index
        return self.hands[self.playerId()][i]

    def privateCardFromColor(self, card, color):
        # get colored jolly from normal jolly
        for c in self.privateCards:
            if c.effect == card.effect and c.color == color:
                return c

    async def set(self, card: Card):
        # check if card is legal then set the card then fire the effect
        hand = self.hands[self.playerId()]

        self.timer.resetTurnTimer()  # reset the timer after a card play

        if card.value == -1:  # check if it's a jolly
            for c in hand:
                if c.effect == card.effect:
                    # if it's a jolly the engine has already set color so find the normal jolly in the hand
                    hand.remove(c)
                    self.deck.append(c)
                    break
        else:
            hand.remove(card)
            self.deck.append(card)

        self.card = card

        if len(hand) == 0:  # if player has no left cards => win. so add it to the winners
            self.winners.append(self.playerId())
            if len(self.winners) == 3:
                self.end = True

            await self.apply(self.card)
        else:
            await self.apply(self.card)

    async def apply(self, card: Card):
        # fire the effect of the set card
        effect = card.effect

        if effect == "+2":
            tmp = self.currentPlayerIndex
            self.next()
            await self.draw(2)
            self.prevPlayerIndex = tmp
        elif effect == "Skip":
            tmp = self.currentPlayerIndex
            self.next()
            self.next()
            self.prevPlayerIndex = tmp
        elif effect == "Reverse":
            self.clockwise = not self.clockwise
            if len(self.winners) != 2:
                self.next()
        elif effect == "+4":
            tmp = self.currentPlayerIndex
            self.next()
            await self.draw(4)
            self.prevPlayerIndex = tmp
        else:
            self.next()

        self.effect_msg = f"{card.effect} {card.color}"

        try:
            await self.botCheck()
        except RecursionError:
            self.effect_msg = "Bots went on cycle shutting down game for safety"
            self.end = True

    async def botCheck(self):
        await self.redraw(self)
        self.timer.resetTurnTimer()  # reset also after a redraw that is very slow

        if self.isBotIndex():  # if it's a bot execute it else => it's a player and timer has been reset
            await self.runBot()

    async def runBot(self):
        if not await self.playBotHand():  # try to play a card
            await self.draw(1, skip=False)  # if the bot can't play any card draw a card
            if not await self.playBotHand():  # try to play a card again
                self.next()  # if no card is still playable skip turn and check if the next player is a bot
                await self.botCheck()

    async def playBotHand(self):
        for card in self.getHand():  # play a card if it's a jolly choose a random color
            if card.color == "Jolly":
                color = ""

                for c in self.getHand():
                    if c.color != "Jolly":
                        color = c.color
                        break

                card = self.privateCardFromColor(card, color if color else random.choice(Game.COLORS))

            if self.canBeSet(card):  # if card can be played, play it and exit the loop
                await self.set(card)
                return True

        return False

    async def draw(self, count: int, player: int = -1, afk=False, skip=True):
        # add a number of cards to the player specified. If no player is passed cards will be added to next player
        for _ in range(count):
            if len(self.deck) > 0:
                if player != -1:
                    self.hands[player].append(self.deck.pop(random.randint(0, len(self.deck) - 1)))
                else:
                    self.hands[self.players[self.currentPlayerIndex]].append(
                        self.deck.pop(random.randint(0, len(self.deck) - 1)))

        self.hands[self.players[self.currentPlayerIndex]].sort(key=sortCards)

        self.effect_msg = "Nothing and has drown 1 card"
        if skip:
            self.next()
            # after a draw if skip is True go to the next player else wait if player wants to play the card
            # if a draw card has been played it's assumed the first next() call has been already made in another method

            # if the user ask to write that the player has drown some cards then write it
            if afk:
                self.effect_msg = "Nothing, has drown 1 card and skipped the turn due to AFK"

            await self.botCheck()

    def next(self):
        # find and set the next player
        self.prevPlayerIndex = self.currentPlayerIndex

        for _ in range(4):  # find the next player, use a for to avoid a loop if something goes wrong
            if self.clockwise:
                self.currentPlayerIndex = clockNext[self.currentPlayerIndex]
            else:
                self.currentPlayerIndex = antiClockNext[self.currentPlayerIndex]

            if self.playerId() not in self.winners:
                break

    def isPrivateEmoji(self, emoji) -> bool:
        # check if card passed is a private card
        for e in self.privateCards:
            if str(e) == emoji:
                return True

        return False

    def dsEmojiLen(self, i) -> int:
        # return how many discord emojis needs to print the number of cards of the give player
        tmp = self.intToEmoji(len(self.getHand(i)))
        tmp = tmp.count(":") // 2
        return tmp if tmp > 0 else 1

    def intToEmoji(self, i) -> str:
        # turn a number into a discord emoji
        emoji = {
            "0": ":zero:",
            "1": ":one:",
            "2": ":two:",
            "3": ":three:",
            "4": ":four:",
            "5": ":five:",
            "6": ":six:",
            "7": ":seven:",
            "8": ":eight:",
            "9": ":nine:"
        }

        tmp = ""
        for c in str(i):
            tmp += emoji[c]

        return "👑" if tmp == ":zero:" else tmp

    def getHand(self, i=-1) -> list:
        # get the hand of the specified player
        return self.hands[self.playerId(i)]

    def canBeSet(self, card):
        return self.card.color == card.color or self.card.value == card.value or card.value == -1

    def isBotIndex(self, i=-1):
        return self.playerId(i) in Game.BOTS


def load(bot):
    # load all uno cards from the bot
    cards = []
    privateCards = []

    for i in range(1, 10):
        cards.append(Card(discord.utils.get(bot.emojis, name=str(i) + "_YELLOW"), "Yellow", i, str(i)))
        cards.append(Card(discord.utils.get(bot.emojis, name=str(i) + "_RED"), "Red", i, str(i)))
        cards.append(Card(discord.utils.get(bot.emojis, name=str(i) + "_BLUE"), "Blue", i, str(i)))
        cards.append(Card(discord.utils.get(bot.emojis, name=str(i) + "_GREEN"), "Green", i, str(i)))

    cards.append(Card(discord.utils.get(bot.emojis, name="SKIP_YELLOW"), "Yellow", 10, "Skip"))
    cards.append(Card(discord.utils.get(bot.emojis, name="SKIP_BLUE"), "Blue", 10, "Skip"))
    cards.append(Card(discord.utils.get(bot.emojis, name="SKIP_GREEN"), "Green", 10, "Skip"))
    cards.append(Card(discord.utils.get(bot.emojis, name="SKIP_RED"), "Red", 10, "Skip"))

    cards.append(Card(discord.utils.get(bot.emojis, name="REVERSE_YELLOW"), "Yellow", 11, "Reverse"))
    cards.append(Card(discord.utils.get(bot.emojis, name="REVERSE_RED"), "Red", 11, "Reverse"))
    cards.append(Card(discord.utils.get(bot.emojis, name="REVERSE_BLUE"), "Blue", 11, "Reverse"))
    cards.append(Card(discord.utils.get(bot.emojis, name="REVERSE_GREEN"), "Green", 11, "Reverse"))

    cards.append(Card(discord.utils.get(bot.emojis, name="PLUS2_YELLOW"), "Yellow", 12, "+2"))
    cards.append(Card(discord.utils.get(bot.emojis, name="PLUS2_GREEN"), "Green", 12, "+2"))
    cards.append(Card(discord.utils.get(bot.emojis, name="PLUS2_BLUE"), "Blue", 12, "+2"))
    cards.append(Card(discord.utils.get(bot.emojis, name="PLUS2_RED"), "Red", 12, "+2"))

    cards.append(Card(discord.utils.get(bot.emojis, name="PLUS4"), "Jolly", -1, "+4"))
    cards.append(Card(discord.utils.get(bot.emojis, name="PLUS4"), "Jolly", -1, "+4"))
    cards.append(Card(discord.utils.get(bot.emojis, name="COLOR_CHANGE"), "Jolly", -1, "Color"))
    cards.append(Card(discord.utils.get(bot.emojis, name="COLOR_CHANGE"), "Jolly", -1, "Color"))

    cards += cards

    cards.append(Card(discord.utils.get(bot.emojis, name=str(0) + "_YELLOW"), "Yellow", 0, "0"))
    cards.append(Card(discord.utils.get(bot.emojis, name=str(0) + "_RED"), "Red", 0, "0"))
    cards.append(Card(discord.utils.get(bot.emojis, name=str(0) + "_BLUE"), "Blue", 0, "0"))
    cards.append(Card(discord.utils.get(bot.emojis, name=str(0) + "_GREEN"), "Green", 0, "0"))

    privateCards.append(Card(discord.utils.get(bot.emojis, name="PLUS4_RED"), "Red", -1, "+4"))
    privateCards.append(
        Card(discord.utils.get(bot.emojis, name="PLUS4_GREEN"), "Green", -1, "+4"))
    privateCards.append(Card(discord.utils.get(bot.emojis, name="PLUS4_BLUE"), "Blue", -1, "+4"))
    privateCards.append(
        Card(discord.utils.get(bot.emojis, name="PLUS4_YELLOW"), "Yellow", -1, "+4"))

    privateCards.append(Card(discord.utils.get(bot.emojis, name="COLOR_RED"), "Red", -1, "Color"))
    privateCards.append(Card(discord.utils.get(bot.emojis, name="COLOR_GREEN"), "Green", -1, "Color"))
    privateCards.append(Card(discord.utils.get(bot.emojis, name="COLOR_BLUE"), "Blue", -1, "Color"))
    privateCards.append(Card(discord.utils.get(bot.emojis, name="COLOR_YELLOW"), "Yellow", -1, "Color"))

    privateCards.append(Card(discord.utils.get(bot.emojis, name="UNO_BACK")))

    privateCards = tuple(privateCards)
    cards = tuple(cards)

    return cards, privateCards
