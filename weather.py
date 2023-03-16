"""
Script to send a daily digest for weather forecasts in the next week that are temperate, clear, and low-ish wind so 
I can plan a long bike ride.

Requires PUSHOVER_USER and PUSHOVER_TOKEN env vars to send push notifications.
"""
import os
import sys
import re
import json
import urllib.request


TAKOMA_PARK_FORECAST_URL = (
    "https://api.weather.gov/gridpoints/LWX/97,75/forecast/hourly"
)
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
USER_AGENT = "github.com/kingishb/good-bike-weather"
WIND_SPEED_REGEX = r"(?P<high>\d+) mph$"

if not PUSHOVER_USER:
    print(f"PUSHOVER_USER required")
    sys.exit(1)

if not PUSHOVER_TOKEN:
    print(f"PUSHOVER_TOKEN required")
    sys.exit(1)

req = urllib.request.Request(TAKOMA_PARK_FORECAST_URL, headers = {"User-Agent": USER_AGENT})

# get weather forecast
with urllib.request.urlopen(req) as resp:
    periods = json.load(resp)["properties"]["periods"]

# find good times to bike
good_time_periods = []
for period in periods:

    # parse wind speed
    m = re.match(WIND_SPEED_REGEX, period["windSpeed"])
    if not m:
        print("could not parse wind speed", period["windSpeed"])
        sys.exit(1)
    wind_speed = int(m["high"])

    if (
        period["isDaytime"]
        and 50 < period["temperature"] < 85
        and period["probabilityOfPrecipitation"]["value"] < 30
        and wind_speed < 15
    ):
        # merge together hourly forecast that make up a block of good weather
        if len(good_time_periods) > 0 and (prev := good_time_periods[-1])["endTime"] == period["startTime"]:
            good_time_periods[-1] = {
                "startTime": prev["startTime"],
                "endTime": period["endTime"],
                "temperature": max(period["temperature"], prev["temperature"]),
                "probabilityOfPrecipitation": max(
                    period["probabilityOfPrecipitation"]["value"],
                    prev["probabilityOfPrecipitation"],
                ),
                "maxWindSpeed": max(wind_speed, prev["maxWindSpeed"]),
            }
        else:
            good_time_periods.append(
                {
                    "startTime": period["startTime"],
                    "endTime": period["endTime"],
                    "temperature": period["temperature"],
                    "probabilityOfPrecipitation": period["probabilityOfPrecipitation"][
                        "value"
                    ],
                    "maxWindSpeed": wind_speed,
                }
            )


if len(good_time_periods) == 0:
    print("😭 no times found!")
    sys.exit(0)

print(good_time_periods)

# build message to send
time_messages = []
for t in good_time_periods:
    time_messages.append(
        f'🚴 {t["startTime"]} - {t["endTime"]} Temp {t["temperature"]} F Precipitation {t["probabilityOfPrecipitation"]}% Wind Speed {t["maxWindSpeed"]} mph'
    )

t = "\n".join(time_messages)
msg = f"""☀️  Great bike weather coming up! 🚲
{t}
Make a calendar entry and get out there!"""

# send push notification
req = urllib.request.Request(
    "https://api.pushover.net/1/messages.json",
    json.dumps({"token": PUSHOVER_TOKEN, "user": PUSHOVER_USER, "message": msg}).encode(
        "utf8"
    ),
    headers={"content-type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    print(json.load(resp))
