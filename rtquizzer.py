#!/usr/bin/env python3
import asyncio
import re
from asyncirc import irc
from enum import IntEnum
import pickle
import asyncirc.plugins.addressed
import threading, time, os, re
import random
random = random.SystemRandom()
import urllib.parse
import requests
import sys
import collections
from datetime import date

#supybot.ircutils (https://github.com/ProgVal/limnoria/tree/master/src/ircutils.py)

class ircutils(object):
    def bold(s):
        """Returns the string s, bolded."""
        return '\x02%s\x02' % s
    
    def italic(s):
        """Returns the string s, italicised."""
        return '\x1D%s\x1D' % s
    
    # Definition of mircColors dictionary moved below because it became an IrcDict.
    def mircColor(s, fg=None, bg=None):
        """Returns s with the appropriate mIRC color codes applied."""
        if fg is None and bg is None:
            return s
        elif bg is None:
            if str(fg) in mircColors:
                fg = mircColors[str(fg)]
            elif len(str(fg)) > 1:
                fg = mircColors[str(fg)[:-1]]
            else:
                # Should not happen
                pass
            return '\x03%s%s\x03' % (fg.zfill(2), s)
        elif fg is None:
            bg = mircColors[str(bg)]
            # According to the mirc color doc, a fg color MUST be specified if a
            # background color is specified.  So, we'll specify 00 (white) if the
            # user doesn't specify one.
            return '\x0300,%s%s\x03' % (bg.zfill(2), s)
        else:
            fg = mircColors[str(fg)]
            bg = mircColors[str(bg)]
            # No need to zfill fg because the comma delimits.
            return '\x03%s,%s%s\x03' % (fg, bg.zfill(2), s)
    
    def stripColor(s):
        """Returns the string s, with color removed."""
        return _stripColorRe.sub('', s)

_stripColorRe = re.compile(r'\x03(?:\d{1,2},\d{1,2}|\d{1,2}|,\d{1,2}|)')
mircColors = {
    'white': '0',
    'black': '1',
    'blue': '2',
    'green': '3',
    'red': '4',
    'brown': '5',
    'purple': '6',
    'orange': '7',
    'yellow': '8',
    'light green': '9',
    'teal': '10',
    'light blue': '11',
    'dark blue': '12',
    'pink': '13',
    'dark grey': '14',
    'light grey': '15',
    'dark gray': '14',
    'light gray': '15',
}

# We'll map integers to their string form so mircColor is simpler.
for (k, v) in list(mircColors.items()):
    if k is not None: # Ignore empty string for None.
        sv = str(v)
        mircColors[sv] = sv
        mircColors[sv.zfill(2)] = sv

class State(IntEnum):
    Question = 0
    Tips = 1
    Pause = 2
    Answer = 3

class Quizbot(object):
    quiz = None
    test = None
    event = None
    questions = {}
    current_question = []
    current_category = ""
    mode = State.Question
    tips = 1
    winner = None
    points = {}
    bot = None
    channel = "#rt-quiz"
    counter = 0
    last = None
    
    def __init__(self, bot):
        self.bot = bot
        self.event = threading.Event()
        self.loadStats()
        self.last = date.today()
        self.quiz = threading.Thread(daemon=True, target=self.quizzing, args=())
        self.quiz.start()
        self.test = threading.Thread(daemon=True, target=self.checkForQuiz, args=())
    
    def sleep(self, timeout : int):
        self.event.wait(timeout)
        self.event.clear()
    
    def loadQuestions(self):
        with open("questions.pickle", "rb") as fobj:
            self.questions = pickle.load(fobj)
    
    def loadStats(self):
        self.points = collections.defaultdict(lambda: 0)
        self.daily = collections.defaultdict(lambda: 0)
        if os.path.isfile("stats.pickle"):
            with open("stats.pickle", "rb") as fobj:
                self.points.update(pickle.load(fobj))
        
        if os.path.isfile("daily.pickle"):
            with open("daily.pickle", "rb") as fobj:
                self.daily.update(pickle.load(fobj))
    
    def reply(self, *args):
        msg = "".join(ircutils.mircColor(i, 2, 0) for i in args)
        self.bot.say(self.channel, msg)
    
    def topic(self, *args):
        topic = "".join(ircutils.mircColor(i, 2, 0) for i in args)
        self.bot.writeln(f'TOPIC {self.channel} :{topic}')
    
    def random(self, r : int):
        return int(random.random() * r)
    
    def checkForQuiz(self):
        while True:
            if not self.quiz.is_alive():
                self.reply("Starte Quiz neu...")
                del self.quiz
                self.quiz = threading.Thread(daemon=True, target=self.quizzing, args=())
                self.quiz.start()
            self.sleep(60)
    
    def quizzing(self):
        while True:
            if self.mode == State.Question:
                self.loadQuestions()
                self.winner = None
                self.tips = 1
                self.counter = 0
                # [category, question, answer]
                
                try:
                    self.current_question = random.choice(self.questions)
                    if not (self.current_question and len(self.current_question) >= 3 and self.validQuestion(self.current_question)):
                        continue
                        continue
                
                    self.reply(f"Kategorie {ircutils.bold(self.current_question[0])}: {self.current_question[1]}")
                    
                    l = len(self.current_question[2])
                    self.current_question.append(l * 2 if l < 80 else l)
                    if not self.random(10):
                        self.reply(ircutils.mircColor("ACHTUNG: Dies ist eine Superpunkterunde. Der Gewinner bekommt die dreifache Punktezahl!", 4, 1))
                        self.current_question[3] *= 3
                
                    self.mode = State.Tips
                
                except Exception as e: # general ignore
                    self.reply(f"Frage konnte nicht geladen werden: {str(e)}")
                
                self.sleep(4)
                continue
        
            elif self.mode == State.Tips:
                if self.counter < 4:
                    self.counter += 1
                    self.sleep(5)
                    continue
                
                self.reply("{}{}{}".format(ircutils.bold("Tipp: "), self.current_question[2][:self.tips], "." * (len(self.current_question[2]) - self.tips)))
                self.tips += 1
                if self.tips >= len(self.current_question[2]):
                    self.counter = 0
                    self.mode = State.Pause
                
                self.sleep(4)
                continue
            
            elif self.mode == State.Pause:
                if not self.counter:
                    self.reply(ircutils.mircColor("Achtung, wenn die Frage innerhalb von 30 Sekunden nicht beantwortet wird, werde ich automatisch eine neue Runde starten!", 3, 1))
                
                if self.counter < 6:
                    self.counter += 1
                    self.sleep(5)
                    continue
                else:
                    self.counter = 0
                    self.mode = State.Answer
            
            elif self.mode == State.Answer:
                if self.winner is not None:
                    x = re.match(r"(.*?).{1}onAir", self.winner, re.IGNORECASE)
                    if x:
                        self.winner = x[1]
                    
                    aliases = {
                        "l-micha" : "lmichael",
                        "spunki" : "lmichael"
                            }
                    
                    if self.winner in aliases:
                        self.winner = aliases[self.winner]
                    
                    if self.winner not in self.points:
                        for k in self.points:
                            if k.lower() == self.winner.lower():
                                self.winner = k
                    self.points[self.winner] += self.current_question[3]
                    self.daily[self.winner] += self.current_question[3]
                    
                    self.reply(f"{self.winner} hat die Antwort", ircutils.mircColor(" " + self.current_question[2] + " ", 7, 1), "korrekt erraten, dafür gibt es", ircutils.mircColor(" " + str(self.current_question[3]) + " ", 4, 1), "Punkte!")
                
                else:
                    self.reply(f"Keiner hat die Antwort", ircutils.mircColor(" " + self.current_question[2] + " ", 7, 1), "korrekt erraten :(")
                
                self.mode = State.Question
                self.current_question = None
                self.current_category = ""
                with open("stats.pickle", "wb") as fobj:
                    pickle.dump(dict(self.points), fobj)
                
                with open("daily.pickle", "wb") as fobj:
                    pickle.dump(dict(self.daily), fobj)
                
                if date.today() - self.last:
                    self.last = date.today()
                    self.daily = collections.defaultdict(lambda: 0)
                
                self.reply(ircutils.mircColor("-------------", 7, 1))
                #self.reply(ircutils.mircColor("Nächste Frage in 20s!", 7, 1))
                #self.reply(ircutils.mircColor("-------------", 7, 1))
                #self.sleep(20)
                self.sleep(5)
    
    def validQuestion(self, q : str) -> bool:
        for i in ["Tipp", "Top 10", "admin@ryobots.de", "Zeit ist vorbei"]:
            if i in q:
                return False
        return True
quiz = None

def git():
    cached = os.stat(__file__).st_mtime
    while True:
        os.system("git pull")
        stamp = os.stat(__file__).st_mtime
        if stamp != cached:
            cached = stamp
            print("Restarting")
            os._exit(0)
        time.sleep(300)

asyncirc.plugins.addressed.register_command_character("!")
bot = irc.connect("irc.euirc.net", 6667, use_ssl=False)
bot.register("RT-Quizzer", "RT-Quizzer", "RT-Quizzer", password="quizzer").join([Quizbot.channel, "#radio-thirty", "#atlantis"])

@bot.on("irc-001")
def connected(par=None):
    global quiz
    quiz = Quizbot(bot)
    threading.Thread(target=git, args=(), daemon=True).start()
    bot.writeln(f"MODE {bot.nick} +B")


@bot.on("addressed")
def on_addressed(message, user, target, text):
    global quiz
    
    def say(target, text):
        text = text.replace("\n", "").replace("\r", "")
        while text:
            bot._writeln(f"PRIVMSG {target} :{text[:400]}")
            text = text[400:]
    
    if target == "#radio-thirty" and text.startswith("wetter"):
        regex_list = {
            re.compile("f.rth") : "fürth"
            }
        cmd = text.split()
        if len(cmd) < 2:
            return
        
        cmd[1] = cmd[1].lower()
        
        if cmd[1] == "moon":
            return
        
        for i in regex_list:
            if i.match(cmd[1]):
                cmd[1] = regex_list[i]
        
        r = requests.get(f"http://de.wttr.in/{urllib.parse.quote(cmd[1])}?Q0T")
        for i, line in enumerate(r.text.splitlines()):
            if i and i % 6 == 0:
                sleep(2)
            say(target, line)
    
    if target != Quizbot.channel or not quiz:
        return
    
    if text in ["punkte", "tag"]:
        for i, p in enumerate(sorted((quiz.daily if text == "tag" else quiz.points).items(), key=lambda x: x[1], reverse=True), start=1):
            quiz.reply(f"{i}.\t{p[0]} ({p[1]})")
            if i >= 10:
                break
    
    elif text == "anzahl":
        quiz.reply(f"{len(quiz.questions)} Fragen")
    
    elif text == "frage":
        quiz.reply(f"Kategorie {ircutils.bold(quiz.current_question[0])}: {quiz.current_question[1]}")

current_category = ""
current_question = []
questions = {}

@bot.on("message")
def on_message(message, user, target, text):
    if target == Quizbot.channel and quiz and quiz.current_question and not quiz.winner and text.lower() == quiz.current_question[2].lower():
        quiz.winner = user.nick
        quiz.mode = State.Answer
        quiz.event.set()
    
    elif target == "#atlantis" :
        if user.nick != "Colin" or not quiz:
            return
    
        global current_category, current_question, questions
        
        x = re.match(r"^(.*?): (.*\??)$", text) # regex by Chipakyu
        if x and quiz:
            current_question = [ircutils.stripColor(x[2]), "", "", 0]
            if not quiz.validQuestion(current_question[0]):
                current_question = []
                return
            
            current_category = ircutils.stripColor(x[1])
        
        print(f"current_category: {current_category}, current_question: {current_question}")
        if not (current_category and current_question):
            return
        
        x = re.match(r"Tipp : .* : (\d*) Punkte", text)
        if x:
            current_question[3] = x[1] // 200
        
        x = re.match(r".*-> (.*) <-.*", text)
        if x:
            current_question[2] = ircutils.stripColor(x[1])
            
            with open("questions.pickle", "rb") as fobj:
                old = pickle.load(fobj)
            
            questions.update(old)
            if current_category not in questions:
                questions[current_category] = [current_question[:]]
            elif current_question not in questions[current_category]:
                questions[current_category].append(current_question[:])
            
            with open("questions.pickle", "wb") as fobj:
                pickle.dump(questions, fobj)
            
            current_question = []
            current_category = ""
    
    elif "freenode staff member" in text.lower():
        bot._writeln(f"KICK {target} {user.nick} :You wrote a bad word")

@bot.on("connection-lost")
def on_disconnected(*args):
    sys.exit(0)

asyncio.get_event_loop().run_forever()
