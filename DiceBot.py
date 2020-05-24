# Dice Bot.py
import os
import random
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# client = discord.Client()
client = commands.Bot(command_prefix="!")

"""
Message should be in format - Set Strat <strat_name>
"""


def update_strat(message: str):
    if message.split(" ")[2] in strats:
        strat.strategy = strats[message.split(" ")[2]]
        return "Updated strategy to " + strat.strategy
    else:
        return "Invalid strategy selection"


def settings():
    return "Current strategy is " + strat.strategy


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    # Command to parse
    if message.content.lower().startswith("roll"):
        results = strat.parse(message.content)
        if results:
            await message.channel.send(results)
    elif message.content.lower().startswith("settings"):
        await message.channel.send(settings())
        return
    elif message.content.lower().startswith("set strat"):
        await message.channel.send(update_strat(message.content))


class Strategy:
    """
    Strategy is interface class declaring operations for all strategies.
    """

    def __init__(self):
        self.desc = ""
        self.message = ""

    def parse(self, message: str):
        if message.__contains__(":"):
            self.desc = message[message.find(":"):]
            self.message = message[0:message.find(":")].lower()
        else:
            self.message = message.lower()
        return ""

    def roll(self, num_dice, num_sides):
        dice = [random.choice(range(1, num_sides + 1)) for _ in range(num_dice)]
        dice.sort()
        return dice

class Generic(Strategy):
    """
    Generic parsing strategy, just rolls what it sees without special processing
    """

    def parse(self, message: str):
        super().parse(message)
        self.message = "".join(self.message.split(" ")[1:])
        match = re.findall("(\+|\-)?([0-9]*)d([0-9]+)", self.message.lower())
        out = []
        for m in match:
            pair = []
            if m[0]:
                pair.append(m[0])
            else:
                pair.append("+")
            roll = self.roll(int(m[1]), int(m[2]))
            pair.append(roll)
            out.append(pair)
        val = 0
        outcome = ""
        for p in out:
            if p[0] == "-":
                val = val - sum(p[1])
            else:
                val = val + sum(p[1])
            outcome = outcome + p[0] + str(p[1]) + " "
        match = re.search("(?:(?:\+|\-)?(?:[0-9]*)d(?:[0-9]+))*((\+|\-)?([0-9]*))", self.message)
        val = val + int(match.group(1))
        outcome = outcome + match.group(1)
        return str(val) + " = " + outcome + " " + self.desc


class ORE(Strategy):
    """
    One Roll Engine parsing, accumulates rolls until a second command is received
    """

    def __init__(self):
        self.results = {}
        super().__init__()

    def roll_all(self):
        results = ""
        for i in range(10, 0, -1):
            if self.results.get(i):
                print("\n".join(self.results.get(i)))
                results = results + "\n".join(self.results.get(i))
        return results

    def parse(self, message: str):
        if message.startswith("roll all"):
            return self.roll_all()
        super().parse(message)
        if not self.desc:
            return "Please add a description"
        self.message = "".join(self.message.split(" ")[1:])
        match = re.search("([0-9]*)hd", self.message)
        if match and match.group(1):
            hd = int(match.group(1))
        elif match: hd = 1
        else: hd = 0
        match = re.search("([0-9]*)wd", self.message)
        if match and match.group(1):
            wd = match.group(1)
        elif match:
            wd = "1"
        else:
            wd = "0"
        match = re.search("([0-9]*)d", self.message)
        if match and match.group(1):
            d = max(min(int(match.group(1)), 10 - hd - int(wd)), 0)
        elif match:
            d = 1
        else:
            d = 0
        roll = self.roll(d, 10)
        #Add hard dice of value 10
        for _ in range(hd):
            roll.append(10)
        outcome = []
        max_height = 0
        #Roll dice
        for i in range(10, 0, -1):
            width = roll.count(i)
            if width > 0 and i > max_height:
                max_height = i
            if width > 2:
                outcome.append((width, ["Width: " + str(width) + ", Height: " + str(i)]))
        if len(outcome) == 0:
            if max(roll) <= 5 and int(wd) < 1:
                outcome.append((0, ["Botch! Loose Max: " + str(max_height)]))
            elif min(roll) >= 6 and int(wd) < 1:
                outcome.append((0, ["Beginner's Luck! Loose Max: " + str(max_height)]))
            elif int(wd) > 0:
                outcome.append((2, ["Saved by the Wild Dice with height: " + str(max_height)]))
            else:
                outcome.append((0, ["Loose Max: " + str(max_height)]))

        # Add wiggle dice
        roll.append(wd + "wd")
        for o in outcome:
            roll.reverse()
            self.results.setdefault(o[0], []).append(" & ".join(o[1]) + " " + str(roll) + " " + self.desc)
        return


class d20(Generic):
    """
    Another name for the Generic strategy
    TODO: Added special rules for advantage and disadvantage
    """

    def parse(self, message: str):
        if message.__contains__("2d20") or message.__contains__("ad") or message.__contains__("dis"):
            self.message = "".join(self.message.split(" ")[1:])
            match = re.findall("(\+|\-)?([0-9]*)d([0-9]+)", self.message.lower())
            out = []
            for m in match:
                pair = []
                if m[0]:
                    pair.append(m[0])
                else:
                    pair.append("+")
                roll = self.roll(int(m[1]), int(m[2]))
                if m[2] == 20 and m[1] == 2:
                    if message.__contains__("ad"):
                        pair.append(roll[1])
                    elif message.__contains__("dis"):
                        pair.append(roll[0])
                else:
                    pair.append(roll)
                out.append(pair)
            val = 0
            outcome = ""
            for p in out:
                if p[0] == "-":
                    val = val - sum(p[1])
                else:
                    val = val + sum(p[1])
                outcome = outcome + p[0] + str(p[1]) + " "
            match = re.search("(?:(?:\+|\-)?(?:[0-9]*)d(?:[0-9]+))*((\+|\-)?([0-9]*))", self.message)
            val = val + int(match.group(1))
            outcome = outcome + match.group(1)
            return str(val) + " = " + outcome + " " + self.desc
        else:
            super().parse(message)

class PbtA(Strategy):
    """
    Powered by the Apocalpyse roller, only needs a modifier to add to rolls
    """

    def parse(self, message: str):
        super().parse(message)
        roll = self.roll(2, 6)
        val = sum(roll) + int(self.message.split(" ")[1])
        if val > 9:
            outcome = "Success!"
        elif val > 6:
            outcome = "Costly Success!"
        else:
            outcome = "Miss"
        return outcome + " " + str(val) + " = " + str(roll) + self.message.split(" ")[1] + " " + self.desc

class SR(Strategy):
    """
    Shadowrun dice roller, rolls a pool of 6 sided dice
    """

    def __init__(self):
        self.init = []
        super().__init__()

    def roll_init(self, message: str):
        if message.lower().__contains__("d"):
            super().parse(message)
            self.message = "".join(self.message.split(" ")[2:])
            match = re.search("([0-9]*)(d|D)6((\+|\-)[0-9]+)", self.message)
            if match:
                mod = match.group(3)
                if match.group(1):
                    dice = match.group(1)
                else:
                    dice = 1
            else:
                match = re.search("([0-9]+)\+([0-9]+)(d|D)6", self.message)
                if match:
                    mod = match.group(1)
                    dice = match.group(2)
                else:
                    return "Error processing initiative"
            roll = self.roll(int(dice), 6)
            score = str(sum(roll)+int(mod)) + " = " + str(roll) + " + " + str(int(mod)) + " " + self.desc
            self.init.append(score)
            return ""
        else:
            self.init.sort(key=lambda scores: int(scores.split(" ")[0]), reverse=True)
            out = ""
            for s in self.init:
                out = out + s + "\n"
            return out

    def parse(self, message: str):
        if message.startswith("roll init"):
            return self.roll_init(message)
        super().parse(message)
        roll = self.roll(int(self.message.split(" ")[1]), 6)
        val = 0
        ones = 0
        for r in roll:
            if r > 4:
                val = val + 1
            elif r == 1:
                ones = ones + 1
        if val == 0 and ones > int(self.message.split(" ")[1])/2:
            outcome = "Critical Glitch! "
        elif ones > int(self.message.split(" ")[1])/2:
            outcome = "Glitch. "
        else: outcome = ""
        return outcome + "Hits: " + str(val) + " " + str(roll) + " " + self.desc


class Parser:
    """
    Container class for the strategies, allowing them to be adjusted by the client
    """

    def __init__(self, strategy: Strategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> str:
        return type(self._strategy).__name__

    @strategy.setter
    def strategy(self, strategy: Strategy) -> None:
        self._strategy = strategy

    def parse(self, message: str) -> None:
        return self._strategy.parse(message)


strats = {"Generic": Generic(), "ORE": ORE(), "d20": d20(), "PbtA": PbtA(),
          "SR": SR()}
strat = Parser(Generic())
client.run(TOKEN)
