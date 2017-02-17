# -*- coding: utf-8 -*-

import sys
import datetime
import time
import urllib
import json
import socket
import re
from slackbot.bot import Bot, listen_to, respond_to


def get_food(day):
    # Get JSON
    URL = 'http://www.hanssonohammar.se/veckansmeny.json'
    response = urllib.urlopen(URL)
    data = json.loads(response.read().decode('utf-8'))

    if day not in data:
        return "(no mat " + str(day) + ")"

    mat_today = data[day][0]

    if 'IKSU' not in mat_today:
        return "(no IKSU today)"

    return "\n".join(mat_today['IKSU'])


@listen_to(r'^compile (.*)$')
def compile(message, code):
    message.reply(u"Jag klarar inte av sånt längre :'(")


@listen_to(r'^run (.*)$')
def run(message, code):
    message.reply(u"Jag klarar inte av sånt längre :'(")


@listen_to(r'^mat(\+*)$')
def mat(message, plus):
    date = datetime.date.fromtimestamp(time.time() + (86400 * len(plus)))
    try:
        message.reply(u"```IKSU - {}\n{}```".format(str(date), get_food(str(date))))
    except Exception as e:
        message.reply(u"Kom inte åt maten 😞 ({what})".format(what=e.message))


@listen_to(ur'^[e\u00E4\u00C4]r.*fredag.*\?', re.IGNORECASE)
def fredag(message):
    if datetime.datetime.today().weekday() == 4:
        message.reply(u"Japp, idag är det fredag! :kreygasm:")
    else:
        message.reply(u"Nej, idag är det INTE fredag! :qq::gun:")


@listen_to(r'^temp(\+*)$')
def temp(message, plus):
    if len(plus) > 0:
        message.reply(u"Jag kan inte se in i framtiden... :qq::gun:")
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('temp.acc.umu.se', 2345))
        tmp = s.recv(1024)
        s.close()
        time, temp = tmp[:len(tmp) - 1].split('=')
        message.reply(u"{} C klockan {}".format(temp, time))


def main():
    bot = Bot()
    bot.run()


if __name__ == '__main__':
    main()
