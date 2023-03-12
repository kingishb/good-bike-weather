// See https://www.weather.gov/documentation/services-web-api for how to find
// your grid coordinates
const TAKOMA_PARK_FORECAST_URL =
  "https://api.weather.gov/gridpoints/LWX/97,75/forecast/hourly";
const PUSHOVER_USER = process.env.PUSHOVER_USER;
const PUSHOVER_TOKEN = process.env.PUSHOVER_TOKEN;
// NOAA asks to identify an application with a unique user agent.
const USER_AGENT = "github.com/kingishb/good-bike-weather";

interface WeatherForecast {
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
  weather: WeatherForecast[];
  error: string;
}> {
  try {
    const resp = await fetch(TAKOMA_PARK_FORECAST_URL, {
      headers: { "User-Agent": USER_AGENT },
    });
    const body = await resp.json();
    const periods: WeatherForecast[] = body.properties.periods;
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

async function push(msg: string): Promise<{ error: string }> {
  try {
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
      return { error: await resp.text() };
    }
  } catch (err) {
    return { error: `error: ${err}` };
  }
  return { error: "" };
}

function parseWindSpeed(windString: string) {
  const rangeRegex = /^(?<low>\d+) to (?<high>\d+) mph$/;
  const match = windString.match(rangeRegex);
  if (match) {
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

function withinFiveDays(dateString: string): boolean {
  const startTime = Date.parse(dateString);
  const now = Date.now();
  const threeDays = 5 * 24 * 60 * 60 * 1000;
  return startTime < now + threeDays;
}

interface weatherPeriod {
  startTime: string;
  endTime: string;
  temperature: number;
  probabilityOfPrecipitation: number;
  maxWindSpeed: number;
}

function fmt(s: string): string {
  return new Date(Date.parse(s)).toLocaleString("en-US", {
    timeZone: "America/New_York",
  });
}

function msg(g: weatherPeriod): string {
  return `🚴 ${fmt(g.startTime)} - ${fmt(g.endTime)}: Temp: ${
    g.temperature
  } F, Precipitation: ${g.probabilityOfPrecipitation}% Wind Speed: ${
    g.maxWindSpeed
  } mph`;
}

function alert(times: weatherPeriod[]) {
  const days: string[] = [];
  for (const t of times) {
    days.push(msg(t));
  }
  return `☀️  Great bike weather coming up! 🚲
  
${days.join("\n")}
  
Make a calendar entry and get out there!`;
}

function filterWeather(forecast: WeatherForecast[]): weatherPeriod[] {
  const timePeriods: weatherPeriod[] = [];
  for (let period of forecast) {
    if (
      period.isDaytime &&
      period.temperature > 50 &&
      period.temperature < 85 &&
      period.probabilityOfPrecipitation.value < 30 &&
      parseWindSpeed(period.windSpeed).high < 15 &&
      withinFiveDays(period.startTime)
    ) {
      // merge together the hourly forecasts with desirable properties to get
      // a time range
      const prev = timePeriods[timePeriods.length - 1];
      if (prev?.endTime === period.startTime) {
        timePeriods[timePeriods.length - 1] = {
          startTime: prev.startTime,
          endTime: period.endTime,
          temperature: Math.max(period.temperature, prev.temperature),
          probabilityOfPrecipitation: Math.max(
            period.probabilityOfPrecipitation.value,
            prev.probabilityOfPrecipitation
          ),
          maxWindSpeed: Math.max(
            parseWindSpeed(period.windSpeed).high,
            prev.maxWindSpeed
          ),
        };
      } else {
        timePeriods.push({
          startTime: period.startTime,
          endTime: period.endTime,
          temperature: period.temperature,
          probabilityOfPrecipitation: period.probabilityOfPrecipitation.value,
          maxWindSpeed: parseWindSpeed(period.windSpeed).high,
        });
      }
    }
  }

  return timePeriods;
}

async function main() {
  if (!PUSHOVER_USER || !PUSHOVER_TOKEN) {
    console.error("PUSHOVER_USER and PUSHOVER_TOKEN required");
    process.exit(1);
  }
  console.log("getting weather...");
  let { weather, error } = await getWeather();
  if (error !== "") {
    console.error(error);
    process.exit(1);
  }

  console.log("checking for good weather...");
  const timesToBike = filterWeather(weather);
  if (timesToBike.length > 0) {
    console.log(timesToBike);
    let { error } = await push(alert(timesToBike));
    if (error) {
      console.error(error);
      process.exit(1);
    }
  } else {
    console.log("no times found 😭");
  }
}

main();
