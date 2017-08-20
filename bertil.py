# -*- coding: utf-8 -*-

import datetime
import time
import urllib
import json
import socket
import re
import random
import requests
from slackbot.bot import Bot, listen_to
from tinydb import TinyDB, Query

def fetch_food_json():
    response = urllib.urlopen('http://www.hanssonohammar.se/veckansmeny.json')
    return json.loads(response.read().decode('utf-8'))

def get_food_from_json(data, day):
    if day not in data:
        return "(no mat " + str(day) + ")"

    mat_today = data[day][0]

    if 'IKSU' not in mat_today:
        return "(no IKSU today)"

    return "\n".join(mat_today['IKSU'])

def get_food(day):
    # Get JSON
    data = fetch_food_json()
    return get_food_from_json(data, day)

@listen_to(r'^veckans mat$')
def veckans_mat(message):
    days = [u"Måndag", u"Tisdag", u"Onsdag", u"Torsdag", u"Fredag"]
    today = datetime.datetime.today().weekday()
    nextweek = 0

    if today > 4:
        nextweek = 7 - today
        today = 0

    data = fetch_food_json()

    fulltext = u""
    for daynum in range(0, len(days) - today):
        date = datetime.date.fromtimestamp(time.time() + (86400 * nextweek) + (86400 * daynum))
        try:
            fulltext += u"\n{}\n{}\n".format(days[today+daynum], get_food_from_json(data, str(date)))
        except Exception as exception:
            if exception.message:
                fulltext += u"\n{}\n{}\n".format(days[today+daynum], exception.message)
            else:
                fulltext += u"\n{}\n{}\n".format(days[today+daynum], u"Okänt fel")

    if fulltext:
        message.reply(u"```{}```".format(fulltext))
    else:
        message.reply(u"Hittade ingen mat.")


@listen_to(r'^vecka$')
def vecka(message):
    week = datetime.datetime.now().isocalendar()[1]
    message.reply(u"Vecka {}".format(week))


@listen_to(r'^datum$')
def datum(message):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    message.reply(u"{}".format(date))


@listen_to(r'^mat(\+*)$')
def mat(message, plus):
    date = datetime.date.fromtimestamp(time.time() + (86400 * len(plus)))
    try:
        message.reply(u"```IKSU - {}\n{}```".format(str(date), get_food(str(date))))
    except Exception as exception:
        message.reply(u"Kom inte åt maten 😞 ({what})".format(what=exception.message))


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


@listen_to(ur'^n[\u00E4\u00C4]r.*helg.*\?', re.IGNORECASE)
def whenhelg(message):
    today = datetime.datetime.now()
    if today.weekday() > 4 or (today.weekday() == 4 and today.hour >= 17):
        message.reply(u"Det är ju redan helg din knasboll! :kreygasm:")
    else:
        weekend = today.replace(hour=17, minute=0, second=0)
        while weekend.weekday() < 4:
            weekend += datetime.timedelta(1)

        diff = weekend - today

        days = diff.days
        hours = diff.seconds / 3600
        minutes = (diff.seconds - hours * 3600) / 60
        seconds = diff.seconds - (hours * 3600) - (minutes * 60)
        message.reply(u"Det är {days} dagar {hours} timmar {minutes} minuter och {seconds} " \
                       "sekunder kvar... :disappointed:".format(days=days, hours=hours,
                                                                minutes=minutes, seconds=seconds))


@listen_to(r'^temp$')
def temp(message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('temp.acc.umu.se', 2345))
    response = sock.recv(1024)
    sock.close()
    current_time, current_temp = response[:len(response) - 1].split('=')
    message.reply(u"{} C klockan {}".format(current_temp, current_time))


@listen_to(r'^quote add (.*)$')
def quote_add(message, quote):
    tdb = TinyDB('/home/simon/bertil/quotes.json')
    tdb.insert({'quote': quote})
    message.reply(u"Quote inlagd!")


@listen_to(r'^quote remove (.*)$')
def quote_remove(message, quote):
    tdb = TinyDB('/home/simon/bertil/quotes.json')
    query = Query()
    if tdb.search(query.quote == quote):
        tdb.remove(query.quote == quote)
        message.reply(u"Tog bort {quote}.".format(quote=quote))
    else:
        message.reply("?")


@listen_to(r'^quote find (.*)$')
def quote_find(message, quote_regex):
    tdb = TinyDB('/home/simon/bertil/quotes.json')
    try:
        query = Query()
        stuff = tdb.search(query.quote.search(quote_regex))
        quotes = [s['quote'] for s in stuff]
        if quotes:
            message.reply(u"Hittade det här:\n```{quotes}```".format(quotes='\n'.join(quotes)))
        else:
            message.reply(u"Hittade inget :-(")
    except Exception as exception:
        message.reply(u"Vad sysslar du med?! ({err})".format(err=exception.message))


@listen_to(r'^quote$')
def get_random_quote(message):
    tdb = TinyDB('/home/simon/bertil/quotes.json')
    quotes = tdb.all()
    if not quotes:
        message.reply(u"Inga quotes inlagda...")
    else:
        quote = random.choice(quotes)
        message.reply(u"```{}```".format(quote['quote']))


@listen_to(r'^so (.*)$')
def stackoverflow(message, query):
    url = 'https://api.stackexchange.com'

    response = requests.get('{}/2.2/search/advanced?q={}&accepted=True' \
                            '&site=stackoverflow'.format(url, query))
    data = response.json()
    items = data['items']
    answers = []

    for item in items:
        answer_id = item['accepted_answer_id']
        answers.append(str(answer_id))

    while len(answers) > 100:
        answers.pop()

    answer_str = ';'.join(answers)
    response = requests.get('{}/2.2/answers/{}?order=desc&sort=activity' \
                            '&site=stackoverflow&filter=withbody'.format(url, answer_str))

    data = response.json()
    items = data['items']
    max_score = 0
    max_answer = None
    for item in items:
        score = item['score']
        if score > max_score:
            max_score = score
            max_answer = item

    body = max_answer['body']
    body = body.replace('<p>', '')
    body = body.replace('</p>', '')
    body = body.replace('<code>', '```')
    body = body.replace('</code>', '```')
    body = body.replace('<ul>', '')
    body = body.replace('</ul>', '')
    body = body.replace('<li>', '* ')
    body = body.replace('</li>', '')
    body = body.replace('<pre>', '')
    body = body.replace('</pre>', '')
    body = body.replace('&lt;', '<')
    body = body.replace('&gt;', '>')
    body = body.replace('<em>', '*')
    body = body.replace('</em>', '*')
    body = body.replace('<strong>', '*')
    body = body.replace('</strong>', '*')

    bodylist = [body for body in body.split('\n') if body]

    while len(bodylist) > 6:
        bodylist.pop()
    bodylist.append('...')

    body = '\n'.join(bodylist)
    body += '\nhttps://stackoverflow.com/a/{}'.format(max_answer['answer_id'])

    message.reply(u"{}".format(body))


def main():
    bot = Bot()
    bot.run()


if __name__ == '__main__':
    main()
