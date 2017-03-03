# -*- coding: utf-8 -*-

import sys
import datetime
import time
import urllib
import json
import socket
import re
import random
from slackbot.bot import Bot, listen_to, respond_to
from tinydb import TinyDB, Query


db = TinyDB('/home/simon/bertil/quotes.json')


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

@listen_to(ur'^[e\u00E4\u00C4]r.*m\u00E5ndag.*\?', re.IGNORECASE)
def mondag(message):
    if datetime.datetime.today().weekday() == 4:
        message.reply(u"Nä det är fredag! :kreygasm:")
    elif datetime.datetime.today().weekday() == 0:
        message.reply(u":joy::gun:")
    else:
        message.reply(u"Nä")

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


@listen_to(r'^quote add (.*)$')
def quote_add(message, quote):
    db.insert({'quote': quote})
    message.reply(u"Quote inlagd!")


@listen_to(r'^quote remove (.*)$')
def quote_remove(message, quote):
    Quote = Query()
    if len(db.search(Quote.quote == quote)) > 0:
        db.remove(Quote.quote == quote)
        message.reply(u"Tog bort {quote}.".format(quote=quote))
    else:
        message.reply("?")


@listen_to(r'^quote find (.*)$')
def quote_find(message, quote_regex):
    try:
        Quote = Query()
        stuff = db.search(Quote.quote.search(quote_regex))
        quotes = [ s['quote'] for s in stuff ]
        if len(quotes) > 0:
            message.reply(u"Hittade det här:\n```{quotes}```".format(quotes='\n'.join(quotes)))
        else:
            message.reply(u"Hittade inget :-(")
    except Exception as e:
        message.reply(u"Vad sysslar du med?! ({err})".format(err=e.message))

@listen_to(r'^quote$')
def quote(message):
    quotes = db.all()
    if len(quotes) == 0:
        message.reply(u"Inga quotes inlagda...")
    else:
        quote = random.choice(quotes)
        message.reply(u"```{}```".format(quote['quote']))


def main():
    bot = Bot()
    bot.run()


if __name__ == '__main__':
    main()
