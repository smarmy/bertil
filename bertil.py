#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import logging
import os.path
import datetime
import time
import urllib
import json
import codecs
import socket
from HTMLParser import HTMLParser
from subprocess import Popen, PIPE
from slackbot.bot import Bot, listen_to, respond_to
from threading import Timer, Lock


SERVICE_PATH = '/home/slackbot/slackbot-service'

# Cache the template text
template_text = None

# Lock for writing, compiling and running IncludeOS service
ios_lock = Lock()


def write_service(code, main):
    template_path = os.path.join(SERVICE_PATH, 'service.cpp.template')
    output_path = os.path.join(SERVICE_PATH, 'service.cpp')

    # Decode HTML entities
    h = HTMLParser()
    code = h.unescape(code)

    # Replace \n in code with \\n
    # So that input such as 'printf("hi\n");' is not written and compiled
    # as 'printf("hi
    #     ");'
    code = code.replace('\n', '\\n')

    # Read template, if not already read
    global template_text
    if template_text is None:
        with codecs.open(template_path, 'r', 'utf-8') as template_file:
            template_text = template_file.read()

    output_text = template_text

    if main:
        # Replace '{% code %}' with 'int main() { {% code %} }'
        output_text = output_text.replace(u'{% code %}', u'int main() { {% code %} }')

    # Replace '{% code %}' with code
    output_text = output_text.replace(u'{% code %}', code)

    # Write output
    with codecs.open(output_path, 'w', 'utf-8') as output_file:
        output_file.write(output_text)


def compile_service():
    command = 'make -C {}'.format(SERVICE_PATH)

    p = Popen(command.split(' '), stdout=PIPE, stderr=PIPE)

    timer = Timer(5, p.kill)
    try:
        timer.start()
        stdout, stderr = p.communicate()
    finally:
        timer.cancel()

    if p.returncode < 0:
        return False, "Timed out"

    elif p.returncode != 0:
        return False, stderr

    else:
        return True, ""


def run_service():
    image_path = os.path.join(SERVICE_PATH, 'Demo_Service.img')
    command = 'qemu-system-x86_64 -drive file={},format=raw,if=ide -nographic -smp 4 -m 64'.format(image_path)

    p = Popen(command.split(' '), stdout=PIPE, stderr=PIPE)

    timer = Timer(5, p.kill)
    try:
        timer.start()
        stdout, stderr = p.communicate()
    finally:
        timer.cancel()

    if p.returncode < 0:
        return "Timed out"
    else:
        return stdout.decode('utf-8')


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
    code = code.decode('utf-8')

    ios_lock.acquire()
    try:
        write_service(code, True)
        ok, error = compile_service()
    finally:
        ios_lock.release()

    if not ok:
        message.reply(u"```\n{}\n```".format(error))
    else:
        message.reply(u"Success!")


@listen_to(r'^run (.*)$')
def run(message, code):
    code = code.decode('utf-8')

    ios_lock.acquire()
    try:
        write_service(code, False)
        ok, error = compile_service()

        if not ok:
            message.reply(u"```\n{}\n```".format(error))
        else:
            output = run_service()
            message.reply(u"```\n{}\n```".format(output))
    finally:
        ios_lock.release()


@listen_to(r'^mat(\+*)$')
def mat(message, plus):
    date = datetime.date.fromtimestamp(time.time() + (86400 * len(plus)))
    message.reply(u"```IKSU - {}\n{}```".format(str(date), get_food(str(date))))


@listen_to(r'^ere fredag\?$')
def fredag(message):
    if datetime.datetime.today().weekday() == 4:
        message.reply(u"JA")
    else:
        message.reply(u"NEJ")


@listen_to(r'^temp$')
def temp(message):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('temp.acc.umu.se', 2345))
    tmp = s.recv(1024)
    s.close()
    time, temp = tmp[:len(tmp) - 1].split('=')
    message.reply(u"{} C klockan {}".format(temp, time))


def main():
    kw = {
            'format': '[%(asctime)s] %(message)s',
            'datefmt': '%m/%d/%Y %H:%M:%S',
            'level': logging.DEBUG,
            'stream': sys.stdout,
            }
    logging.basicConfig(**kw)
    bot = Bot()
    bot.run()


if __name__ == '__main__':
    main()
