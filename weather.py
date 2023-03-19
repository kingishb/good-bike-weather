"""
Script to send a daily digest of weather forecasts in the next week that are 
temperate, clear, and low-ish wind so I can plan a long bike ride.
"""
import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime
from pprint import pprint

USER_AGENT = "github.com/kingishb/good-bike-weather"
WIND_SPEED_REGEX = r"(?P<high>\d+) mph$"

parser = argparse.ArgumentParser()
parser.add_argument("noaa_url", help="forecast url at api.weather.gov")
parser.add_argument("pushover_user", help="pushover user")
parser.add_argument("pushover_token", help="pushover token")
args = parser.parse_args()


def fmt(time):
    return datetime.fromisoformat(time).strftime("%A, %B %d %I:%M%p")


def main():

    req = urllib.request.Request(
        args.noaa_url, headers={"User-Agent": USER_AGENT}
    )

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
            and period["probabilityOfPrecipitation"]["value"] < 30
            # tolerate a little more wind if it's warmer, a "light breeze"
            # in 50-60 degrees a "gentle breeze" when temp is 60-80
            # src: https://www.weather.gov/pqr/wind
            and (
                (50 < period["temperature"] < 60 and wind_speed < 7)
                or (60 < period["temperature"] < 80 and wind_speed < 12)
            )
        ):
            # merge together hourly forecast that make up a block of good weather
            if (
                len(good_time_periods) > 0
                and (prev := good_time_periods[-1])["endTime"] == period["startTime"]
            ):
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
                        "probabilityOfPrecipitation": period[
                            "probabilityOfPrecipitation"
                        ]["value"],
                        "maxWindSpeed": wind_speed,
                    }
                )

    if len(good_time_periods) == 0:
        print("😭 no times found!")
        sys.exit(0)

    pprint(good_time_periods)

    # build message to send
    time_messages = []
    for t in good_time_periods:
        time_messages.append(
            f'🚴 {fmt(t["startTime"])} - {fmt(t["endTime"])}, Temp {t["temperature"]} F, Precipitation {t["probabilityOfPrecipitation"]}%, Wind Speed {t["maxWindSpeed"]} mph'
        )

    t = "\n".join(time_messages)
    msg = f"""☀️  Great bike weather coming up! 🚲
    {t}
    Make a calendar entry and get out there!"""

    # send push notification
    req = urllib.request.Request(
        "https://api.pushover.net/1/messages.json",
        json.dumps(
            {"token": args.pushover_token, "user": args.pushover_user, "message": msg}
        ).encode("utf8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        print(json.load(resp))


if __name__ == "__main__":
    main()
