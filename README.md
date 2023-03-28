<img src="screenshot.jpg" width=300/>

Github action that tells me when to go biking.

Uses NOAA's [weather API](https://www.weather.gov/documentation/services-web-api) and [Pushover](https://pushover.net/).

Usage:
```
usage: weather.py [-h] [--debug] [--cli] noaa_url pushover_user pushover_token

positional arguments:
  noaa_url        forecast url at api.weather.gov
  pushover_user   pushover user
  pushover_token  pushover token

options:
  -h, --help      show this help message and exit
  --debug         print all the forecasts to look at and the message, don't send push alert
  --cli           print message to stdout without sending a push alert
```
