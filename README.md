<img src="screenshot.jpg" width=300/>

Github action that tells me when to go biking.

Uses NOAA's [weather API](https://www.weather.gov/documentation/services-web-api) and [Pushover](https://pushover.net/).

Usage:
```
> python weather.py -h
usage: weather.py [-h] noaa_url pushover_user pushover_token

positional arguments:
  noaa_url        forecast url at api.weather.gov
  pushover_user   pushover user
  pushover_token  pushover token

options:
  -h, --help      show this help message and exit
```
