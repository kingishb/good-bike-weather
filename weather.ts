/*
About:
Tells Brian good times to ride his bike with the NWS API and Pushover.

Good to ride bike when:
    - temp is between 50-80 degrees
    - not a lot of wind
    - no precipitation
    - is daytime


Get Takoma Park's weather coords:
curl -L https://api.weather.gov/points/37.97973,-77.00462

Get Takoma Park's weather forecast 
curl https://api.weather.gov/gridpoints/AKQ/57,98/forecast | jq .properties.periods returns an array like:

            {
                "number": 6,
                "name": "Monday",
                "startTime": "2023-03-13T06:00:00-04:00",
                "endTime": "2023-03-13T18:00:00-04:00",
                "isDaytime": true,
                "temperature": 52,
                "temperatureUnit": "F",
                "temperatureTrend": null,
                "probabilityOfPrecipitation": {
                    "unitCode": "wmoUnit:percent",
                    "value": 80
                },
                "dewpoint": {
                    "unitCode": "wmoUnit:degC",
                    "value": 6.1111111111111107
                },
                "relativeHumidity": {
                    "unitCode": "wmoUnit:percent",
                    "value": 100
                },
                "windSpeed": "3 to 9 mph",
                "windDirection": "N",
                "icon": "https://api.weather.gov/icons/land/day/rain,80/rain,60?size=medium",
                "shortForecast": "Light Rain",
                "detailedForecast": "Rain. Mostly cloudy, with a high near 52. Chance of precipitation is 80%. New rainfall amounts between a quarter and half of an inch possible."
            },
*/

// Takoma Park
const FORECAST_URL = "https://api.weather.gov/gridpoints/AKQ/57,98/forecast";

// NOAA API Response
interface APIWeatherForecast {
  number: number;
  name: string;
  startTime: string;
  endTime: string;
  isDaytime: boolean;
  temperature: number;
  temperatureUnit: string;
  temperatureTrend: any;
  probabilityOfPrecipitation: ProbabilityOfPrecipitation;
  dewpoint: Dewpoint;
  relativeHumidity: RelativeHumidity;
  windSpeed: string;
  windDirection: string;
  icon: string;
  shortForecast: string;
  detailedForecast: string;
}

interface ProbabilityOfPrecipitation {
  unitCode: string;
  value: number;
}

interface Dewpoint {
  unitCode: string;
  value: number;
}

interface RelativeHumidity {
  unitCode: string;
  value: number;
}

async function getWeather(): Promise<{
  weather: APIWeatherForecast[];
  error: string;
}> {
  try {
    // @ts-ignore
    const resp = await fetch(FORECAST_URL);
    const body = await resp.json();
    // @ts-ignore
    const periods: APIWeatherForecast[] = body.properties.periods;
    if (resp.status > 299) {
      return {
        weather: [],
        error: `NOAA API returned error - ${resp.status} - ${JSON.stringify(
          resp.body
        )}`,
      };
    }

    return {
      weather: periods,
      error: "",
    };
  } catch (err) {
    return { weather: [], error: `error: ${err}` };
  }
}

function parseWindSpeed(windString: string) {
  const rangeRegex = /^(?<low>\d+) to (?<high>\d+) mph$/;
  if (windString.match(rangeRegex)) {
    const match = windString.match(rangeRegex);
    return {
      low: parseInt(match?.groups?.low || "0"),
      high: parseInt(match?.groups?.high || "0"),
    };
  } else {
    const singleRegex = /^(?<mph>\d+) mph$/;
    const match = windString.match(singleRegex);
    const range = parseInt(match?.groups?.mph || "0");
    return { low: range, high: range };
  }
}

interface goodTimes {
  day: string;
  startTime: string;
  endTime: string;
  temperature: number;
  probabilityOfPrecipitation: number;
  maxWindSpeed: number;
}
function filterWeather(apiResponse: APIWeatherForecast[]): goodTimes[] {
  const goodTimesToBike: goodTimes[] = [];
  for (let period of apiResponse) {
    if (
      period.isDaytime &&
      period.temperature > 50 &&
      period.temperature < 80 &&
      period.probabilityOfPrecipitation.value < 20 &&
      parseWindSpeed(period.windSpeed).high < 20
    ) {
      goodTimesToBike.push({
        day: period.name,
        startTime: period.startTime,
        endTime: period.endTime,
        temperature: period.temperature,
        probabilityOfPrecipitation: period.probabilityOfPrecipitation.value,
        maxWindSpeed: parseWindSpeed(period.windSpeed).high,
      });
    }
  }
  return goodTimesToBike;
}

async function main() {
  const { weather, error } = await getWeather();
  if (error !== "") {
    console.error(error);
    return;
  }

  const timesToBike = filterWeather(weather);
  console.log(timesToBike);
}

main();
