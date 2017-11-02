import datetime
import json
import requests

def fetch_food_json():
    response = requests.get('http://www.hanssonohammar.se/veckansmeny.json').text
    return json.loads(response)


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


# Takes a year, returns a year worth of json from api.dryg.net
# See https://api.dryg.net/ for json format
def get_swedish_year(year):
    return requests.get('https://api.dryg.net/dagar/v2.1/{year}'.format(
        year=year)).json()


# Takes a year and a month, returns a month worth of json from api.dryg.net
def get_swedish_month(year, month):
    return requests.get('https://api.dryg.net/dagar/v2.1/{year}/{month}'.format(
        year=year, month=month)).json()


# Takes a year, a month and a day, returns an array containing a weeks
# worth of json aquired from api.dryg.net representing the week in which
# the date sent to function resides
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

    today_index = len(month_before_json) + date.day - 1
    monday_index = today_index - date.weekday()
    sunday_index = today_index + (7 - date.weekday())

    all_days = sum([month_before_json, month_json, month_after_json], [])

    return all_days[monday_index:sunday_index]


# Returns an array containing the current week in json from api.dryg.net
def get_current_swedish_week():
    today = datetime.datetime.today()
    return get_swedish_week(today.year, today.month, today.day)


# Takes a year, month and day, returns the json string representing
# this day aquired from api.dryg.net
def get_swedish_day(year, month, day):
    return requests.get('https://api.dryg.net/dagar/v2.1/{year}/{month}/{day}'.format(
        year=year, month=month, day=day)).json()


# Takes an array with a weeks worth of json from api.dryg.net along
# with a weekday index. Makes a shitty guess and returns True if the
# day is a squeeze day, False otherwise, _highly_ unreliable
def is_squeeze_day(weekday_index, week_json):
    day_before = weekday_index - 1 if weekday_index > 0 else weekday_index
    day_after = weekday_index + 1 if weekday_index < 6 else weekday_index

    return (week_json[day_before]['röd dag'] == 'Ja' or
            week_json[day_after]['röd dag'] == 'Ja')


# Takes a day json string from api.dryg.net
# Returns True if day is Workfree, False otherwise
def is_workfree_day(day):
    return day['arbetsfri dag'] == 'Ja'