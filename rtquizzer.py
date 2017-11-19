#!/usr/bin/env python3
import asyncio
import re
from asyncirc import irc
from enum import IntEnum
import pickle
import asyncirc.plugins.addressed
import threading, time, os, re
import random
import sys

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
    
    def __init__(self, bot):
        self.bot = bot
        self.loadStats()
        self.quiz = threading.Thread(daemon=True, target=self.quizzing, args=())
        self.quiz.start()
        self.test = threading.Thread(daemon=True, target=self.checkForQuiz, args=())
    
    def loadQuestions(self):
        with open("questions.pickle", "rb") as fobj:
            self.questions = pickle.load(fobj)
            self.questions = {key : [[entry.strip() for entry in question if isinstance(entry, str)] for question in self.questions[key]] for key in self.questions}
    
    def loadStats(self):
        if os.path.isfile("stats.pickle"):
            with open("stats.pickle", "rb") as fobj:
                self.points = pickle.load(fobj)
    
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
            time.sleep(60)
    
    def quizzing(self):
        while True:
            if self.mode == State.Question:
                self.loadQuestions()
                self.winner = None
                self.tips = 1
                self.counter = 0
                #text = [f"Kategorie {ircutils.bold(self.current_category)}: ", ircutils.mircColor(self.current_question[0], 11, 2)]
                
                try:
                    try:
                        self.current_category = random.choice(list(self.questions.keys()))
                        self.current_question = random.choice(self.questions[self.current_category])
                        if self.current_category.count(":") > 1:
                            parts = self.current_category.split(":", 1)
                            try:
                                self.questions[self.current_category].remove(self.current_question)
                            except (KeyError, ValueError):
                                pass
                            
                            self.current_category = parts[0]
                            self.current_question[0] = f"{parts[1]}{self.current_question[0]}"
                            
                            if self.current_category in self.questions:
                                self.questions[self.current_category] = [self.current_question]
                            else:
                                self.questions[self.current_category].append(self.current_question)
                        
                        text = [f"Kategorie {ircutils.bold(self.current_category)}: {self.current_question[0]}"]
                    
                    
                    except IndexError:
                        text = [f"Kategorie {ircutils.bold(self.current_category)}: Frage '{self.current_question}' fehlerhaft."]
                        try:
                            self.questions[self.current_category].remove(self.current_question)
                        except ValueError:
                            text.append("Konnte Frage nicht aus der Datenbank tilgen.")
                        except KeyError: # we change the question above
                            pass
                        
                        try:
                            with open("questions.pickle", "wb") as fobj:
                                pickle.dump(self.questions, fobj)
                        except Exception as e:
                            text.append(f"Konnte Datenbank nicht auf die Festplatte schreiben: {str(e)}. Dies ist ein schwerer Fehler, bitte sofort den Botinhaber kontaktieren!")
                            raise
                
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
                
                except Exception as e: # general ignore
                    self.reply(f"Frage konnte nicht geladen werden: {str(e)}")
                
                time.sleep(4)
                continue
        
            elif self.mode == State.Tips:
                if self.counter < 4:
                    self.counter += 1
                    time.sleep(5)
                    continue
                
                self.reply(ircutils.mircColor("{}{}{}".format(ircutils.bold("Tipp: "), self.current_question[2][:self.tips], "." * (len(self.current_question[2]) - self.tips)), 0, 10))
                self.tips += 1
                if self.tips >= len(self.current_question[2]):
                    self.counter = 0
                    self.mode = State.Pause
                
                time.sleep(4)
                continue
            
            elif self.mode == State.Pause:
                if not self.counter:
                    self.reply(ircutils.mircColor("Achtung, wenn die Frage innerhalb von 60 Sekunden nicht beantwortet wird, werde ich automatisch eine neue Runde starten!", 3, 1))
                
                if self.counter < 12:
                    self.counter += 1
                    time.sleep(5)
                    continue
                else:
                    self.counter = 0
                    self.mode = State.Answer
            
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
                with open("stats.pickle", "wb") as fobj:
                    pickle.dump(self.points, fobj)
                
                self.reply(ircutils.mircColor("-------------", 7, 1))
                #self.reply(ircutils.mircColor("Nächste Frage in 20s!", 7, 1))
                #self.reply(ircutils.mircColor("-------------", 7, 1))
                #time.sleep(20)
                time.sleep(5)
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
bot.register("RT-Quizzer", "RT-Quizzer", "RT-Quizzer", password="quizzer").join([Quizbot.channel, "#atlantis"])

@bot.on("irc-001")
def connected(par=None):
    global quiz
    quiz = Quizbot(bot)
    threading.Thread(target=git, args=(), daemon=True).start()
    bot.writeln(f"MODE {bot.nick} +B")


@bot.on("addressed")
def on_addressed(message, user, target, text):
    if target != Quizbot.channel:
        return
    
    global quiz
    
    if text == "punkte" and quiz:
        for i, p in enumerate(sorted(quiz.points.items(), key=lambda x: x[1], reverse=True), start=1):
            quiz.reply(f"{i}.\t{p[0]} ({p[1]})")
            if i > 5:
                break
    
    elif text == "anzahl" and quiz:
        i = 0
        for key in quiz.questions:
            i += len(quiz.questions[key])
        
        quiz.reply(f"{i} Fragen")

current_category = ""
current_question = []
questions = {}

@bot.on("message")
def on_message(message, user, target, text):
    if target == Quizbot.channel and quiz and quiz.current_question and not quiz.winner and text.lower() == quiz.current_question[2].lower():
        quiz.winner = user.nick
        quiz.mode = State.Answer
    
    elif target == "#atlantis" :
        if user.nick != "Colin":
            return
    
        global current_category, current_question, questions
        
        x = re.match(r"^(.*?): (.*\??)$", text) # regex by Chipakyu
        if x and "Tipp" not in text:
            current_question = [ircutils.stripColor(x[2]), "", "", 0]
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

@bot.on("connection-lost")
def on_disconnected(*args):
    sys.exit(0)
asyncio.get_event_loop().run_forever()
