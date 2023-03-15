import os
import sys
import re

import requests

TAKOMA_PARK_FORECAST_URL = (
    "https://api.weather.gov/gridpoints/LWX/97,75/forecast/hourly"
)
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
if not PUSHOVER_USER:
    print(f"PUSHOVER_USER required")
    sys.exit(1)

PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
if not PUSHOVER_TOKEN:
    print(f"PUSHOVER_TOKEN required")
    sys.exit(1)

USER_AGENT = "github.com/kingishb/good-bike-weather"
WIND_SPEED_REGEX = r"(?P<high>\d+) mph$"


# get weather forecast
resp = requests.get(TAKOMA_PARK_FORECAST_URL)
if resp.status_code > 299:
    print(f"NOAA API error: {resp.status_code} - resp.body")
    sys.exit(1)

periods = resp.json()["properties"]["periods"]

# find good times to bike
time_periods = []
for period in periods:
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
        # merge together hourly forecast if they make up a block of good weather
        if len(time_periods) > 0:
            prev = time_periods[-1]
            if prev["endTime"] == period["startTime"]:
                time_periods[-1] = {
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
                time_periods.append(
                    {
                        "startTime": period["startTime"],
                        "endTime": period["endTime"],
                        "temperature": period["temperature"],
                        "probabilityOfPrecipitation": period[
                            "probabilityOfPrecipitation"
                        ]["value"],
                        "maxWindSpeed": wind_speed,
                    }
                )
        else:
            time_periods.append(
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
if len(time_periods) == 0:
    print("😭 no times found!")
    sys.exit(0)

print(time_periods)

# build message to send
time_messages = []
for t in time_periods:
    time_messages.append(
        f'🚴 {t["startTime"]} - {t["endTime"]} Temp {t["temperature"]} F Precipitation {t["probabilityOfPrecipitation"]}% Wind Speed {t["maxWindSpeed"]} mph'
    )

t = "\n".join(time_messages)
msg = f"""☀️  Great bike weather coming up! 🚲
{t}
Make a calendar entry and get out there!"""

# send push notification
requests.post(
    "https://api.pushover.net/1/messages.json",
    json={"token": PUSHOVER_TOKEN, "user": PUSHOVER_USER, "message": msg},
)
