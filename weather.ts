/*
Get Takoma Park's weather coords:
curl -L https://api.weather.gov/points/37.97973,-77.00462

Get Takoma Park's weather forecast 
curl https://api.weather.gov/gridpoints/AKQ/57,98/forecast | jq .properties.periods returns an array like:
*/

// Takoma Park
const FORECAST_URL = "https://api.weather.gov/gridpoints/AKQ/57,98/forecast";
const PUSHOVER_USER = process.env.PUSHOVER_USER;
const PUSHOVER_TOKEN = process.env.PUSHOVER_TOKEN;

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

async function push(msg: string) {
  const resp = await fetch("https://api.pushover.net/1/messages.json", {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({
      token: PUSHOVER_TOKEN,
      user: PUSHOVER_USER,
      message: msg,
    }),
  });
  if (resp.status > 299) {
    console.error("pushover failed :(", await resp.text());
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

function withinThreeDays(dateString: string): bool {
  const startTime = Date.parse(dateString);
  const now = Date.now();
  const threeDays = 3 * 24 * 60 * 60 * 1000;
  return startTime < now + threeDays;
}

interface goodTime {
  day: string;
  startTime: string;
  endTime: string;
  temperature: number;
  probabilityOfPrecipitation: number;
  maxWindSpeed: number;
}

function msg(g: goodTime): string {
  return `${g.day} is a great day to bike 🚴. Temp: ${
    g.temperature
  }, Precipitation: ${g.probabilityOfPrecipitation * 100}%m Wind Speed: ${
    g.maxWindSpeed
  }`;
}

function alert(times: goodTime[]) {
  const days: string[] = [];
  for (const t of times) {
    days.push(msg(t));
  }
  return `😎 Great biking potential in your future! 😎
  
  ${days.join("\n")}
  
  Make a calendar entry and get out there!`;
}
function filterWeather(apiResponse: APIWeatherForecast[]): goodTime[] {
  const goodTimesToBike: goodTime[] = [];
  for (let period of apiResponse) {
    if (
      period.isDaytime &&
      period.temperature > 50 &&
      period.temperature < 80 &&
      period.probabilityOfPrecipitation.value < 20 &&
      parseWindSpeed(period.windSpeed).high < 20 &&
      withinThreeDays(period.startTime)
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
  if (!PUSHOVER_USER || !PUSHOVER_TOKEN) {
    console.error("PUSHOVER_USER and PUSHOVER_TOKEN required");
    process.exit(1);
  }
  const { weather, error } = await getWeather();
  if (error !== "") {
    console.error(error);
    process.exit(1);
  }

  const timesToBike = filterWeather(weather);
  if (timesToBike.length > 0) {
    console.log(timesToBike);
    await push(alert(timesToBike));
  } else {
    console.log("no times found 😭");
  }
}

main();
