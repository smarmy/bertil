# -*- coding: utf-8 -*-

import datetime
import time
import urllib.request
import urllib.parse
import urllib.error
import json
import socket
import re
import random
import requests

from slackbot.bot import Bot, listen_to
from slackbot.manager import PluginsManager

from tinydb import TinyDB, Query

from apiclient.discovery import build
from apiclient.errors import HttpError

import bertil_secrets


def fetch_food_json():
    response = urllib.request.urlopen('http://www.hanssonohammar.se/veckansmeny.json')
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

def get_swedish_year(year):
    return requests.get('https://api.dryg.net/dagar/v2.1/{year}'.format(
        year=year)).json()

def get_swedish_month(year, month):
    return requests.get('https://api.dryg.net/dagar/v2.1/{year}/{month}'.format(
        year=year, month=month)).json()

def get_swedish_week(year, month, day):
    month_json = get_swedish_month(year, month)['dagar']
    month_before_json = None
    month_after_json = None

    date = datetime.date(year, month, day)

    if month == 1:
        month_before_json = get_swedish_month(year - 1, 12)['dagar']
        month_after_json = get_swedish_month(year, month + 1)['dagar']
    elif month == 12:
        month_before_json = get_swedish_month(year, month - 1)['dagar']
        month_after_json = get_swedish_month(year + 1, 1)['dagar']
    else:
        month_before_json = get_swedish_month(year, month - 1)['dagar']
        month_after_json = get_swedish_month(year, month + 1)['dagar']

    today_index = len(month_json) + date.day
    monday_index = today_index - date.weekday()
    sunday_index = today_index + (7 - date.weekday())

    all_days = sum([month_before_json, month_json, month_after_json], [])

    return all_days[monday_index:sunday_index]

def get_current_swedish_week():
    today = datetime.datetime.today()
    return get_swedish_week(today.year, today.month, today.day)

def get_swedish_day(year, month, day):
    return requests.get('https://api.dryg.net/dagar/v2.1/{year}/{month}/{day}'.format(
        year=year, month=month, day=day)).json()

# shitty squeeze day...
def is_squeeze_day(year, month, day):
    date = datetime.date(year, month, day)
    week_json = get_swedish_week(year, month, day)
    start_day = date.weekday() - 1 if date.weekday() > 0 else date.weekday()
    end_day = date.weekday() + 1 if date.weekday() < 6 else date.weekday()

    return (week_json[start_day]['röd dag'] == 'Ja' or
            week_json[end_day]['röd dag'] == 'Ja')

def is_workfree_day(year, month, day):
    day = get_swedish_day(year, month, day)['dagar'][0]
    return day['arbetsfri dag'] == 'Ja'

@listen_to(r'^help$')
def bertil_help(message):
    func_names = [p.pattern for p, _ in PluginsManager.commands['listen_to'].items()]
    message.reply('Jag kan följade kommandon:\n```{}```'.format('\n'.join(func_names)))


@listen_to(r'^veckans mat$')
def veckans_mat(message):
    days = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]
    today = datetime.datetime.today().weekday()
    nextweek = 0

    if today > 4:
        nextweek = 7 - today
        today = 0

    data = fetch_food_json()

    fulltext = ""
    for daynum in range(0, len(days) - today):
        date = datetime.date.fromtimestamp(time.time() + (86400 * nextweek) + (86400 * daynum))
        try:
            fulltext += "\n{}\n{}\n".format(days[today+daynum],
                                            get_food_from_json(data, str(date)))
        except Exception as exception:
            if str(exception):
                fulltext += "\n{}\n{}\n".format(days[today+daynum], str(exception))
            else:
                fulltext += "\n{}\n{}\n".format(days[today+daynum], "Okänt fel")

    if fulltext:
        message.reply("```{}```".format(fulltext))
    else:
        message.reply("Hittade ingen mat.")


@listen_to(r'^vecka$')
def vecka(message):
    week = datetime.datetime.now().isocalendar()[1]
    message.reply("Vecka {}".format(week))


@listen_to(r'^datum$')
def datum(message):
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    message.reply("{}".format(date))


@listen_to(r'^mat(\+*)$')
def mat(message, plus):
    date = datetime.date.fromtimestamp(time.time() + (86400 * len(plus)))
    try:
        message.reply("```IKSU - {}\n{}```".format(str(date), get_food(str(date))))
    except Exception as exception:
        message.reply("Kom inte åt maten 😞 ({what})".format(what=str(exception)))


@listen_to(r'^youtube(.*)')
def youtube(message, query):
    developer_key = bertil_secrets.YOUTUBE_API_KEY
    youtube_api_service_name = 'youtube'
    youtube_api_version = 'v3'
    max_results = 1

    try:
        youtube_api = build(youtube_api_service_name,
                            youtube_api_version,
                            developerKey=developer_key)

        search_response = youtube_api.search().list(
            q=query,
            part='id, snippet',
            maxResults=max_results
        ).execute()

    except HttpError as err:
        message.reply('HTTP error {} happen:\n{}'.format(err.resp.status, err.content))

    videos = []

    for search_result in search_response.get('items', []):
        if search_result['id']['kind'] == 'youtube#video':
            videos.append('{} (https://www.youtube.com/watch?v={})'.format(
                search_result['snippet']['title'],
                search_result['id']['videoId']))

    message.reply('{}'.format('\n'.join(videos)))


@listen_to(r'^[e\u00E4\u00C4]r.*m\u00E5ndag.*\?', re.IGNORECASE)
def mondag(message):
    if datetime.datetime.today().weekday() == 4:
        message.reply("Nä det är fredag! :kreygasm:")
    elif datetime.datetime.today().weekday() == 0:
        message.reply(":joy::gun:")
    else:
        message.reply("Nä")


@listen_to(r'^[e\u00E4\u00C4]r.*fredag.*\?', re.IGNORECASE)
def fredag(message):
    if datetime.datetime.today().weekday() == 4:
        message.reply("Japp, idag är det fredag! :kreygasm:")
    else:
        message.reply("Nej, idag är det INTE fredag! :qq::gun:")


@listen_to(r'^n[\u00E4\u00C4]r.*hem.*\?', re.IGNORECASE)
def hem(message):
    message.reply("Det är väl bara att gå")


@listen_to(r'^n[\u00E4\u00C4]r.*helg.*\?', re.IGNORECASE)
def whenhelg(message):
    today = datetime.datetime.now()
    if today.weekday() > 4 or (today.weekday() == 4 and today.hour >= 17):
        message.reply("Det är ju redan helg din knasboll! :kreygasm:")
    else:
        weekend = today.replace(hour=17, minute=0, second=0)
        while weekend.weekday() < 4:
            weekend += datetime.timedelta(1)

        diff = weekend - today

        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds - hours * 3600) // 60
        seconds = diff.seconds - (hours * 3600) - (minutes * 60)
        message.reply("Det är {days} dagar {hours} timmar {minutes} minuter och {seconds} " \
                       "sekunder kvar... :disappointed:".format(days=days, hours=hours,
                                                                minutes=minutes, seconds=seconds))


@listen_to(r'^temp$')
def temp(message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('temp.acc.umu.se', 2345))
    response = sock.recv(1024)
    sock.close()
    response_str = response.decode('ascii')
    current_time, current_temp = response_str[:len(response_str) - 1].split('=')
    message.reply("{} C klockan {}".format(current_temp, current_time))


@listen_to(r'^quote add (.*)$')
def quote_add(message, quote):
    tdb = TinyDB('/home/simon/bertil/quotes.json')
    tdb.insert({'quote': quote})
    message.reply("Quote inlagd!")


@listen_to(r'^quote remove (.*)$')
def quote_remove(message, quote):
    tdb = TinyDB('/home/simon/bertil/quotes.json')
    query = Query()
    if tdb.search(query.quote == quote):
        tdb.remove(query.quote == quote)
        message.reply("Tog bort {quote}.".format(quote=quote))
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
            message.reply("Hittade det här:\n```{quotes}```".format(quotes='\n'.join(quotes)))
        else:
            message.reply("Hittade inget :-(")
    except Exception as exception:
        message.reply("Vad sysslar du med?! ({err})".format(err=str(exception)))


@listen_to(r'^quote$')
def get_random_quote(message):
    tdb = TinyDB('/home/simon/bertil/quotes.json')
    quotes = tdb.all()
    if not quotes:
        message.reply("Inga quotes inlagda...")
    else:
        quote = random.choice(quotes)
        message.reply("```{}```".format(quote['quote']))


@listen_to(r'^so (.*)$')
def stackoverflow(message, query):
    url = 'https://api.stackexchange.com'

    # Search for question and retrieve answer id
    search_url = '{}/2.2/search/advanced?order=desc&sort=votes&accepted=True' \
                 '&site=stackoverflow&q={}'.format(url, query)
    response_json = requests.get(search_url).json()
    if not response_json['items']:
        message.reply('Inga träffar! :-(')
        return
    question = response_json['items'][0]
    answer_id = question['accepted_answer_id']

    # Get answer
    answer_url = '{}/2.2/answers/{}?&site=stackoverflow&filter=withbody'.format(url, answer_id)
    response_json = requests.get(answer_url).json()
    answer = response_json['items'][0]
    answer_body = answer['body']

    # Only reply with first 6 rows in answer
    reply = '\n'.join([body for body in answer_body.split('\n')[:6]])
    reply += '\n...'
    reply += '\nhttps://stackoverflow.com/a/{}'.format(answer_id)

    # Format for Slack
    reply = reply.replace('<p>', '')
    reply = reply.replace('</p>', '')
    reply = reply.replace('<code>', '```')
    reply = reply.replace('</code>', '```')
    reply = reply.replace('<ul>', '')
    reply = reply.replace('</ul>', '')
    reply = reply.replace('<li>', '* ')
    reply = reply.replace('</li>', '')
    reply = reply.replace('<pre>', '')
    reply = reply.replace('</pre>', '')
    reply = reply.replace('&lt;', '<')
    reply = reply.replace('&gt;', '>')
    reply = reply.replace('<em>', '*')
    reply = reply.replace('</em>', '*')
    reply = reply.replace('<strong>', '*')
    reply = reply.replace('</strong>', '*')

    message.reply("{}".format(reply))


@listen_to(r'^fika(\+*)$')
def fika(message, plus):
    fikalistan = [
        'simon',
        'kev',
        'mancus',
        'hansson',
        'ps',
        'tomas',
        'matilda',
    ]
    fikalistan_start = 40

    week = datetime.datetime.now().isocalendar()[1] + len(plus)
    fikalistan_index = (week - fikalistan_start) % len(fikalistan)
    person = fikalistan[fikalistan_index]

    message.reply('Vecka {} har {} fika!'.format(week, person))


@listen_to(r'^ica$')
def ica(message):
    access_token = bertil_secrets.FB_ACCESS_TOKEN
    url = 'https://graph.facebook.com/v2.10/IcaAlidhem/feed?access_token={}'.format(access_token)
    response_json = requests.get(url).json()
    for entry in response_json['data']:
        if 'lunch' in entry['message']:
            today = datetime.datetime.now().date()
            entry_date_str = entry['created_time'].split('T')[0]
            entry_date = datetime.datetime.strptime(entry_date_str, '%Y-%m-%d').date()
            if entry_date == today:
                message.reply(entry['message'])
            else:
                message.reply('Senaste lunchinlägget är från {} :-('.format(entry_date))
            return

    message.reply('Hittade ingen lunch :-(')


@listen_to(r'^\$(.*)')
def matte(message, math_string):
    string = urllib.parse.quote_plus(math_string)
    string = requests.get("http://api.mathjs.org/v1/?expr={}".format(string)).text
    message.reply(string)

@listen_to(r'^.*bertil[?!]*$')
def hmm(message):
    message.reply('Vad saru?')

def main():
    bot = Bot()
    bot.run()


if __name__ == '__main__':
    main()
