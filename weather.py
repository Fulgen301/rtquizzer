#!/usr/bin/env python3
import asyncio
from asyncirc import irc
import asyncirc.plugins.addressed
import requests

asyncirc.plugins.addressed.register_command_character("!")

weather = irc.connect("irc.euirc.net", 6667, use_ssl=False)
weather.register("RT-Weather", "RT-Weather", "RT-Weather").join(["#radio-thirty"])

@weather.on("irc-001")
def connected(par=None):
    weather.writeln(f"MODE {weather.nick} +B")

@weather.on("addressed")
def on_addressed(message, user, target, text):
    if text.startswith("wetter"):
        cmd = text.split()
        print(cmd)
        if len(cmd) < 2:
            return
        
        r = requests.get(f"http://de.wttr.in/{cmd[1]}?Q0T")
        for line in r.text.splitlines():
            weather.say(target, line)

asyncio.get_event_loop().run_forever()
