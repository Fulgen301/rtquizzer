#!/usr/bin/env python3
import asyncio
import re
from asyncirc import irc
from enum import IntEnum
import json

import supybot.ircutils as ircutils
import asyncirc.plugins.addressed
import threading, time, os
import random
import sys

class State(IntEnum):
    Question = 0
    Tips = 1
    Answer = 2

class Quizbot(object):
    quiz = None
    questions = {}
    current_question = []
    current_category = ""
    mode = State.Question
    tips = 1
    winner = None
    points = {}
    bot = None
    channel = "#rt-quiz"
    
    def __init__(self, bot):
        self.bot = bot
        self.loadStats()
        self.quiz = threading.Thread(daemon=True, target=self.quizzing, args=())
        self.quiz.start()
    
    def loadQuestions(self):
        with open("questions.json", "r") as fobj:
            self.questions = json.load(fobj)
            self.questions = {key : [[entry.strip() for entry in question if isinstance(entry, str)] for question in self.questions[key]] for key in self.questions}
    
    def loadStats(self):
        if os.path.isfile("stats.json"):
            with open("stats.json", "r") as fobj:
                self.points = json.load(fobj)
    
    def reply(self, *args):
        msg = "".join(ircutils.mircColor(i, 2, 0) for i in args)
        self.bot.say(self.channel, msg)
    
    def topic(self, *args):
        topic = "".join(ircutils.mircColor(i, 2, 0) for i in args)
        self.bot.writeln(f'TOPIC {self.channel} :{topic}')
    
    def random(self, r : int):
        return int(random.random() * r)
    
    def quizzing(self):
        print("quizzing()")
        while True:
            if self.mode == State.Question:
                self.loadQuestions()
                self.winner = None
                self.tips = 1
                self.current_category = random.choice(list(self.questions.keys()))
                self.current_question = random.choice(self.questions[self.current_category])[:]
                text = [f"Kategorie {ircutils.bold(self.current_category)}: ", ircutils.mircColor(self.current_question[0], 11, 2)]
                self.reply(*text)
                self.topic(*text)
                try:
                    self.current_question[3] = len(self.current_question[2]) * 2
                except IndexError:
                    while len(self.current_question) < 4:
                        self.current_question.append("")
                    self.current_question[3] = len(self.current_question[2]) * 2
                
                if not self.random(10):
                    self.reply(ircutils.mircColor("ACHTUNG: Dies ist eine Superpunkterunde. Der Gewinner bekommt die dreifache Punktezahl!", 4, 1))
                    self.current_question[3] *= 3
                
                self.mode = State.Tips
                time.sleep(4)
                continue
        
            elif self.mode == State.Tips:
                self.reply("{}{}{}".format(ircutils.bold("Tipp: "), self.current_question[2][:self.tips], "." * (len(self.current_question[2]) - self.tips)))
                self.tips += 1
                if self.tips == len(self.current_question[2]):
                    self.mode = State.Answer
                
                time.sleep(4)
                continue
            elif self.mode == State.Answer:
                if self.winner is not None:
                    if self.winner not in self.points:
                        self.points[self.winner] = self.current_question[3]
                    else:
                        self.points[self.winner] += self.current_question[3]
                    
                    self.reply(f"{self.winner} hat die Antwort", ircutils.mircColor(" " + self.current_question[2] + " ", 7, 1), "korrekt erraten, dafür gibt es", ircutils.mircColor(" " + str(self.current_question[3]) + " ", 4, 1), "Punkte!")
                
                else:
                    self.reply(f"Keiner hat die Antwort", ircutils.mircColor(" " + self.current_question[2] + " ", 7, 1), "korrekt erraten :(")
                
                if self.current_question[1]:
                    self.reply("Zusatzinfo:")
                    self.reply(f"{self.current_question[1]}")
                
                self.mode = State.Question
                self.current_question = None
                self.current_category = ""
                with open("stats.json", "w") as fobj:
                    json.dump(self.points, fobj)
                
                self.reply(ircutils.mircColor("-------------", 7, 1))
                self.reply(ircutils.mircColor("Nächste Frage in 20s!", 7, 1))
                self.reply(ircutils.mircColor("-------------", 7, 1))
                time.sleep(20)
quiz = None

asyncirc.plugins.addressed.register_command_character("!")
bot = irc.connect("irc.euirc.net", 6667, use_ssl=False)
bot.register("RT-Quizzer", "RT-Quizzer", "RT-Quizzer").join([Quizbot.channel])

@bot.on("irc-001")
def connected(par=None):
    global quiz
    quiz = Quizbot(bot)
@bot.on("addressed")
def on_addressed(message, user, target, text):
    global quiz
    
    if text == "punkte" and quiz:
        for i, key in enumerate(sorted(quiz.points), start=1):
            quiz.reply(f"{i}.\t{key} ({quiz.points[key]})")
            
            if i > 5:
                break

@bot.on("message")
def on_message(message, user, target, text):
    if target == Quizbot.channel and quiz and quiz.current_question and not quiz.winner and text.lower() == quiz.current_question[2].lower():
        quiz.winner = user.nick
        quiz.mode = State.Answer

@bot.on("connection-lost")
def on_disconnected(*args):
    sys.exit(2)
asyncio.get_event_loop().run_forever()
