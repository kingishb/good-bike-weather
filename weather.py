"""
Script to send a daily digest of weather forecasts in the next week that are 
temperate, clear, and low-ish wind so I can plan a long bike ride.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime


def pretty_datetime(time):
    """Formats an ISO 8601 timestamp in the format 'Tuesday, March 28 01:00PM'"""
    return datetime.fromisoformat(time).strftime("%A, %B %d %I:%M%p")


def pretty_time(time):
    """Formats an ISO 8601 timestamp in the format '06:00PM'"""
    return datetime.fromisoformat(time).strftime("%I:%M%p")


def weather_forecast(url):
    """Download the weather forecast from NOAA's weather API, parsing the
    wind speed."""

    req = urllib.request.Request(
        url, headers={"User-Agent": "github.com/kingishb/good-bike-weather"}
    )

    periods = []
    # get weather forecast with a couple of retries
    for i in range(3):
        try:
            with urllib.request.urlopen(req) as resp:
                periods = json.load(resp)["properties"]["periods"]
                break
        except urllib.error.HTTPError as e:
            print("http error", e)
            time.sleep(2**i)

    if len(periods) == 0:
        print("error: could not load forecast")
        sys.exit(1)

    wind_speed_regex = r"(?P<high>\d+) mph$"
    for p in periods:
        # parse wind speed
        m = re.match(wind_speed_regex, p["windSpeed"])
        if not m:
            print("error: could not parse wind speed", p["windSpeed"])
            sys.exit(1)
        p["parsedWindSpeed"] = int(m["high"])

    return periods


def merge_append_forecast(time_periods, hourly_forecast):
    """Add an hourly forecast to a list of desirable forecast periods.
    If it runs together with the previous hourly forecast, merge together
    the two forecasts."""
    if (
        len(time_periods) > 0
        and (prev := time_periods[-1])["endTime"] == hourly_forecast["startTime"]
    ):
        time_periods[-1] = {
            "startTime": prev["startTime"],
            "endTime": hourly_forecast["endTime"],
            "temperature": max(hourly_forecast["temperature"], prev["temperature"]),
            "probabilityOfPrecipitation": max(
                hourly_forecast["probabilityOfPrecipitation"]["value"],
                prev["probabilityOfPrecipitation"],
            ),
            "maxWindSpeed": max(
                hourly_forecast["parsedWindSpeed"], prev["maxWindSpeed"]
            ),
        }
    else:
        time_periods.append(
            {
                "startTime": hourly_forecast["startTime"],
                "endTime": hourly_forecast["endTime"],
                "temperature": hourly_forecast["temperature"],
                "probabilityOfPrecipitation": hourly_forecast[
                    "probabilityOfPrecipitation"
                ]["value"],
                "maxWindSpeed": hourly_forecast["parsedWindSpeed"],
            }
        )


def build_message(good_time_periods, low_wind_periods):
    """Build weather report to send."""

    good_times = []
    for t in good_time_periods:
        good_times.append(
            f'🚴 {pretty_datetime(t["startTime"])} - {pretty_time(t["endTime"])}, Temp {t["temperature"]} F, Precipitation {t["probabilityOfPrecipitation"]}%, Wind Speed {t["maxWindSpeed"]} mph'
        )
    gt = "\n".join(good_times)

    not_windy_times = []
    for t in low_wind_periods:
        not_windy_times.append(
            f'🚴 {pretty_datetime(t["startTime"])} - {pretty_time(t["endTime"])}, Temp {t["temperature"]} F, Precipitation {t["probabilityOfPrecipitation"]}%, Wind Speed {t["maxWindSpeed"]} mph'
        )
    nw = "\n".join(not_windy_times)
    msg = "🚲 Cycling weather report 🚲"
    if len(good_time_periods) > 0:
        msg += f"""

☀️  Great bike weather!
{gt}"""
    if len(not_windy_times) > 0:
        msg += f"""

🧤🧣 A little chilly, but you can do it! 
{nw}"""
    msg += "\n\nMake a calendar entry and get out there!\n"
    return msg


def push(msg, pushover_user, pushover_token):
    """Send push notification."""
    req = urllib.request.Request(
        "https://api.pushover.net/1/messages.json",
        json.dumps(
            {"token": pushover_token, "user": pushover_user, "message": msg}
        ).encode("utf8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        print(json.load(resp))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("noaa_url", help="forecast url at api.weather.gov")
    parser.add_argument("pushover_user", help="pushover user")
    parser.add_argument("pushover_token", help="pushover token")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="print all the forecasts to look at and the message, don't send push alert",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="print message to stdout without sending a push alert",
    )
    args = parser.parse_args()

    periods = weather_forecast(args.noaa_url)

    # good times to bike
    good_time_periods = []

    # colder, but at least low wind
    low_wind_periods = []

    for period in periods:

        if period["isDaytime"] and period["probabilityOfPrecipitation"]["value"] < 25:
            # src: https://www.weather.gov/pqr/wind
            if (
                50 <= period["temperature"] <= 65 and period["parsedWindSpeed"] < 13
            ) or (65 < period["temperature"] <= 83 and period["parsedWindSpeed"] <= 18):
                merge_append_forecast(good_time_periods, period)

            elif 32 <= period["temperature"] <= 50 and period["parsedWindSpeed"] < 8:
                merge_append_forecast(low_wind_periods, period)

    if args.debug:
        for p in periods:
            if p["isDaytime"]:
                print(
                    pretty_datetime(p["startTime"]),
                    "temp",
                    p["temperature"],
                    "wind",
                    p["parsedWindSpeed"],
                    "precipitation",
                    p["probabilityOfPrecipitation"]["value"],
                )

    msg = build_message(good_time_periods, low_wind_periods)

    if args.cli or args.debug:
        print(msg)
        return

    push(msg, args.pushover_user, args.pushover_token)


if __name__ == "__main__":
    main()
