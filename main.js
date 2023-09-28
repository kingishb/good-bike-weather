const noaa = "https://api.weather.gov/gridpoints/LWX/97,75/forecast/hourly";
const pushover = "https://api.pushover.net/1/messages.json";
const fmt = (date) => new Date(Date.parse(date)).toLocaleString();
const time = (date) => fmt(date).split(",")[1];

async function retry(fn, n) {
  for (let i = 0; i < n; i++) {
    try {
      await fn();
      return;
    } catch (err) {
      console.log(err);
    }
    const backoff = 1000 * Math.floor(Math.random() * 2 ** i);
    await new Promise((r) => setTimeout(r, backoff));
  }
}

async function run() {
  const temperate = (
    await (await fetch(noaa)).json()
  ).properties.periods.filter(
    (p) =>
      p.isDaytime &&
      p.probabilityOfPrecipitation.value < 25 &&
      p.temperature > 50 &&
      parseInt(p.windSpeed.split(" ")[0]) < 13
  );
  const blocks = [];
  let num = temperate.length === 0 ? temperate[0].number : 0;
  for (const p of temperate) {
    if (p.number === num + 1 && blocks.length > 0) {
      const last = blocks.pop();
      last.endTime = p.endTime;
      blocks.push(last);
    } else {
      blocks.push(p);
    }
    num = p.number;
  }
  const schedule = blocks
    .map((p) => `${fmt(p.startTime)} to${time(p.endTime)}`)
    .join("\n");
  const msg = `bike times 🚲
${schedule}`;

  await fetch(pushover, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      token: process.env.PUSHOVER_TOKEN,
      user: process.env.PUSHOVER_USER,
      message: msg,
    }),
  });
}

await retry(run, 3);
