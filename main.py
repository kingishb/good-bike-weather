import datetime
import json
import os
import random
import time
import urllib.request

noaa = "https://api.weather.gov/gridpoints/LWX/97,75/forecast/hourly"
pushover = "https://api.pushover.net/1/messages.json"


def fmt_date(d):
    return datetime.datetime.fromisoformat(d).strftime("%a %I:%M %p")


def fmt_time(d):
    return datetime.datetime.fromisoformat(d).strftime("%I:%M %p")


def retry(fn, n):
    for i in range(n):
        try:
            fn()
            return
        except Exception as e:
            print(e)
            backoff = random.randint(0, 2**i)
            time.sleep(backoff)


def run():
    with urllib.request.urlopen(noaa) as response:
        data = json.loads(response.read().decode())

    temperate = [
        p
        for p in data["properties"]["periods"]
        if p["isDaytime"]
        and p["probabilityOfPrecipitation"]["value"] < 25
        and p["temperature"] > 50
        and int(p["windSpeed"].split(" ")[0]) < 13
    ]

    blocks = []
    num = temperate[0]["number"] if len(temperate) == 0 else 0

    for period in temperate:
        if period["number"] == num + 1 and len(blocks) > 0:
            last = blocks.pop()
            last["endTime"] = period["endTime"]
            blocks.append(last)
        else:
            blocks.append(period)
        num = period["number"]

    schedule = "\n".join(
        [f"{fmt_date(b['startTime'])} to {fmt_time(b['endTime'])}" for b in blocks]
    )

    msg = f"bike times 🚲\n{schedule}"
    print(msg)

    headers = {"content-type": "application/json"}

    payload = json.dumps(
        {
            "token": os.environ.get("PUSHOVER_TOKEN"),
            "user": os.environ.get("PUSHOVER_USER"),
            "message": msg,
        }
    ).encode("utf-8")

    req = urllib.request.Request(pushover, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req) as response:
        print(response.status_code)


retry(run, 3)
