import datetime
import time
import urllib.parse
import socket
import re
import random
import subprocess
import json
import requests

from slackbot.bot import Bot, listen_to, respond_to, default_reply
from slackbot.manager import PluginsManager

from tinydb import TinyDB, Query

from apiclient.discovery import build
from apiclient.errors import HttpError

import markovify

import utils
import bertil_secrets

@listen_to(r'^help$')
def bertil_help(message):
    func_names = [p.pattern for p, _ in PluginsManager.commands['listen_to'].items()]
    message.reply('Jag kan följade kommandon:\n```{}```'.format('\n'.join(func_names)))

@listen_to(r'^veckans mat(\s*konst)?$')
def veckans_mat(message, restaurant):
    if restaurant is None:
        restaurant = 'IKSU'
    else:
        restaurant = 'KONST'

    days = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]
    today = datetime.datetime.today().weekday()
    nextweek = 0

    if today > 4:
        nextweek = 7 - today
        today = 0

    data = utils.fetch_food_json()

    fulltext = "Veckans mat på {}:".format(restaurant)
    for daynum in range(0, len(days) - today):
        date = datetime.date.fromtimestamp(time.time() + (86400 * nextweek) + (86400 * daynum))
        try:
            fulltext += "\n{}\n{}\n".format(days[today+daynum],
                                            utils.get_food_from_json(data, restaurant, str(date)))
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

@listen_to(r'^mat(\+*)(\s*konst)?$')
def mat(message, plus, restaurant):
    date = datetime.date.fromtimestamp(time.time() + (86400 * len(plus)))

    if restaurant is None:
        restaurant = 'IKSU'
    else:
        restaurant = 'KONST'

    try:
        message.reply("```{} - {}\n{}```".format(restaurant,
                                                 str(date),
                                                 utils.get_food(restaurant, str(date))))
    except Exception as exception:
        message.reply("Kom inte åt maten från {} 😞 ({what})".format(restaurant,
                                                                    what=str(exception)))

@listen_to(r'^youtube\s*(.*)')
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
    week = utils.get_current_swedish_week()
    days = 0

    for day in week[today.weekday():len(week)]:
        day_index = int(day['dag i vecka']) - 1
        if (not utils.is_workfree_day(day) and not
                utils.is_squeeze_day(day_index, week)):
            days += 1

    hours = 0
    if today.hour < 8 or today.hour > 17:
        days -= 1
    else:
        hours = 17 - today.hour

    reactions = [':kreygasm:',
                 ':relieved:',
                 ':neutral_face:'
                 ':disappointed::gun:',
                 ':disappointed::noose:',
                ]

    if days <= 0 and hours == 0:
        message.reply('Det är ju redan helg! :kreygasm:')
    else:
        message.reply('Det är {days} dagar och {hours} timmar kvar till' \
                      'helgen... {reaction}'.format(days=days,
                                                    hours=hours,
                                                    reaction=reactions[days]))

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
        'mancus',
        'hansson',
        'kapker',
        'ps',
        'tomas',
        'matilda',
        'simon',
    ]
    fikalistan_start = 6

    week = datetime.datetime.now().isocalendar()[1] + len(plus)
    fikalistan_index = (week - fikalistan_start) % len(fikalistan)
    person = fikalistan[fikalistan_index]

    message.reply('Vecka {} har @{} fika!'.format(week, person))

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

@default_reply
@listen_to(r'bertil')
@listen_to(r'^markov$')
def bertil(message):
    markov(message, None)

@listen_to(r'^markov (\S+)$')
def markov(message, stuff):
    if not hasattr(markov, "text_model"):
        with open('/home/simon/bertil/user_messages.json') as file_:
            user_messages = json.load(file_)

        messages = ''
        for user in user_messages:
            messages += '\n'.join(user_messages[user])

        markov.text_model = markovify.NewlineText(messages, state_size=3)

    if stuff:
        try:
            response = markov.text_model.make_sentence_with_start(stuff, False, tries=64)
            message.send(response)
            return
        except Exception:
            message.send("Jag kommer inte på något att säga med {} :rip:".format(stuff))

    else:
        response = markov.text_model.make_sentence(tries=64)
        if not response:
            message.send("Jag lyckades inte generera en mening :rip:")
        else:
            message.send(response)

@listen_to(r'^markovmat$')
def markov_mat(message):
    markov_mat_stuff(message, None)

@listen_to(r'^markovmat (\S+)$')
def markov_mat_stuff(message, stuff):
    if not hasattr(markov_mat, "text_model"):
        with open('/home/simon/bertil/mat.txt') as file_:
            mat_text = file_.read()

        markov_mat.text_model = markovify.NewlineText(mat_text, state_size=1)

    if stuff:
        response = ""
        for _ in range(512):
            response = markov_mat.text_model.make_sentence(tries=64)
            if not response:
                continue
            if stuff.lower() in response.lower():
                message.send(response)
                return

        message.send("Jag kunde inte hitta på en maträtt med {} :rip:".format(stuff))

    else:
        response = markov_mat.text_model.make_sentence(tries=64)
        if not response:
            message.send("Jag lyckades inte generera en mening :rip:")
        else:
            message.send(response)

@listen_to(r'^status$')
def status(message):
    result = subprocess.run(['ssh', 'gamma', '/home/simon/status/status.sh'],
                            stdout=subprocess.PIPE)
    message.reply("```{}```".format(result.stdout.decode('ascii')))

@respond_to(r'^help$')
def bertil_private_help(message):
    func_names = [p.pattern for p, _ in PluginsManager.commands['respond_to'].items()]
    message.reply('Jag kan följade kommandon:\n```{}```'.format('\n'.join(func_names)))

@respond_to(r'^s\u00E4g (.*)$')
def speak(message, text):
    message.reply("Åkejrå, skickar till #general. Hoppas de inte skjuter budbäraren... :qq: :gun:")
    message.body['channel'] = 'C2R7P4B8B'
    message.send(text)

def main():
    random.seed()
    bot = Bot()
    bot.run()

if __name__ == '__main__':
    main()
