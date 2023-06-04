use chrono::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::thread;
use std::time::Duration;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let pushover_user = std::env::var("PUSHOVER_USER")?;
    let pushover_token = std::env::var("PUSHOVER_TOKEN")?;
    let noaa_url = "https://api.weather.gov/gridpoints/LWX/97,75/forecast/hourly";
    let pushover_url = "https://api.pushover.net/1/messages.json";

    // fetch weather forecast
    let resp = get_forecast_with_retries(noaa_url)?;

    // Pick some times that are warm, not raining, and during the daytime
    // src: https://www.weather.gov/pqr/wind
    let mut periods = vec![];
    // TODO: if it's above freezing, maybe try very low wind for colder months
    for period in resp.properties.periods.iter() {
        if period.is_daytime && period.probability_of_precipitation.value < 25 {
            if period.temperature >= 50 && period.temperature <= 65 {
                let wind_speed = parse_wind_speed(&period.wind_speed);
                if wind_speed < 13 {
                    periods.push(period);
                }
            } else if period.temperature > 65 && period.temperature <= 83 {
                let wind_speed = parse_wind_speed(&period.wind_speed);
                if wind_speed <= 18 {
                    periods.push(period);
                }
            }
        }
    }

    // Combine time periods that run together and build them into a message
    let entries: Vec<String> = coalesce(periods).iter().map(|time| time.pretty()).collect();
    let msg = format!(
        "☀️Good bike times in the next 7 days☀️\n{}",
        entries.join("\n")
    );
    println!("{}", msg);

    // send message to pushover
    let mut m = std::collections::HashMap::new();
    m.insert("token", pushover_token);
    m.insert("user", pushover_user);
    m.insert("message", msg);

    let client = reqwest::blocking::Client::new();
    client.post(pushover_url).json(&m).send()?;

    Ok(())
}


// fetch weather forecast with some retries and exponential backoff
fn get_forecast_with_retries(url: &str) -> Result<NOAAForecast, reqwest::Error> {
    let client = reqwest::blocking::Client::new();
    let mut i = 0;
    loop {
        let resp =  client
            .get(url)
            .header(
                "user-agent",
                "https://github.com/kingishb/good-days-to-bike",
            )
            .send()?;

            match resp.json::<NOAAForecast>()
        {
            Ok(v) => return Ok(v), 
            Err(e) => {
                if i < 3 {
                    let exp: u64 = 2;
                    thread::sleep(Duration::from_secs(exp.pow(i)));
                    i += 1;
                    continue;
                } else {
                    return Err(e);
                }
            }
        }
    }
}

// Parse a string like "12 mph" to the number 12.
fn parse_wind_speed(s: &str) -> u8 {
    s.split(' ')
        .next()
        .unwrap_or("255")
        .parse::<u8>()
        .unwrap_or(u8::MAX)
}

#[derive(Debug)]
struct TimePeriod {
    start_time: String,
    end_time: String,
    temp: i64,
    probability_of_precipitation: i64,
    max_wind_speed: u8,
}

impl TimePeriod {
    // Format a string to send as a text message for a weather forecast period
    fn pretty(&self) -> String {
        let start = DateTime::parse_from_rfc3339(&self.start_time)
            .unwrap()
            .format("%A, %B %d %I:%M%p");
        let end = DateTime::parse_from_rfc3339(&self.end_time)
            .unwrap()
            .format("%I:%M%p");

        format!(
            "🚲 {0} - {1} temp {2}F precipitation {3}% wind speed {4} mph",
            start, end, self.temp, self.probability_of_precipitation, self.max_wind_speed
        )
    }
}

// Coalesce time periods that run together, reporting the max temperature and wind speed
fn coalesce(periods: Vec<&Period>) -> Vec<TimePeriod> {
    let mut tp: Vec<TimePeriod> = vec![];
    for cur in periods.into_iter() {
        if !tp.is_empty() {
            let mut prev = tp.pop().unwrap();
            if prev.end_time == cur.start_time {
                prev.end_time = cur.end_time.clone();
                prev.temp = std::cmp::max(prev.temp, cur.temperature);
                prev.probability_of_precipitation = std::cmp::max(
                    prev.probability_of_precipitation,
                    cur.probability_of_precipitation.value,
                );
                prev.max_wind_speed =
                    std::cmp::max(prev.max_wind_speed, parse_wind_speed(&cur.wind_speed));
                tp.push(prev);
            } else {
                tp.push(prev);
                tp.push(TimePeriod {
                    start_time: cur.start_time.clone(),
                    end_time: cur.end_time.clone(),
                    temp: cur.temperature,
                    probability_of_precipitation: cur.probability_of_precipitation.value,
                    max_wind_speed: parse_wind_speed(&cur.wind_speed),
                });
            }
        } else {
            tp.push(TimePeriod {
                start_time: cur.start_time.clone(),
                end_time: cur.end_time.clone(),
                temp: cur.temperature,
                probability_of_precipitation: cur.probability_of_precipitation.value,
                max_wind_speed: parse_wind_speed(&cur.wind_speed),
            });
        }
    }
    tp
}

// Autogenerated types for NOAA's web API.
// Created with JSON to Serde: https://transform.tools/json-to-rust-serde
#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct NOAAForecast {
    #[serde(rename = "@context")]
    context: (String, Context),
    #[serde(rename = "type")]
    type_field: String,
    geometry: Geometry,
    properties: Properties,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Context {
    #[serde(rename = "@version")]
    version: String,
    wx: String,
    geo: String,
    unit: String,
    #[serde(rename = "@vocab")]
    vocab: String,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Geometry {
    #[serde(rename = "type")]
    type_field: String,
    coordinates: Vec<Vec<Vec<f64>>>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Properties {
    updated: String,
    units: String,
    forecast_generator: String,
    generated_at: String,
    update_time: String,
    valid_times: String,
    elevation: Elevation,
    periods: Vec<Period>,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Elevation {
    unit_code: String,
    value: f64,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Period {
    number: i64,
    name: String,
    start_time: String,
    end_time: String,
    is_daytime: bool,
    temperature: i64,
    temperature_unit: String,
    temperature_trend: Value,
    probability_of_precipitation: ProbabilityOfPrecipitation,
    dewpoint: Dewpoint,
    relative_humidity: RelativeHumidity,
    wind_speed: String,
    wind_direction: String,
    icon: String,
    short_forecast: String,
    detailed_forecast: String,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct ProbabilityOfPrecipitation {
    unit_code: String,
    value: i64,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Dewpoint {
    unit_code: String,
    value: f64,
}

#[derive(Default, Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RelativeHumidity {
    unit_code: String,
    value: i64,
}
