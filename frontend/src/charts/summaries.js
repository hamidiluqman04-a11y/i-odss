import { formatNumber } from "../services/format";

/*
 * Plain-language text alternatives for the charts. Screen readers cannot read
 * an SVG chart, so each chart exposes one of these as its accessible name;
 * every chart card also has a "Table" view with all the values.
 */

function extremes(items, valueOf) {
  let high = items[0];
  let low = items[0];
  for (const item of items) {
    if (valueOf(item) > valueOf(high)) high = item;
    if (valueOf(item) < valueOf(low)) low = item;
  }
  return { high, low };
}

export function weeklySalesSummary(data) {
  if (!data.length) return "Line chart of units sold per week: no data.";
  const { high, low } = extremes(data, (d) => d.units);
  const last = data[data.length - 1];
  return (
    `Line chart of units sold per week over ${data.length} weeks. ` +
    `Highest: ${high.week}, ${formatNumber(high.units)} units. Lowest: ${low.week}, ${formatNumber(low.units)} units. ` +
    `Most recent: ${last.week}, ${formatNumber(last.units)} units.`
  );
}

export function barSummary(data, formatValue, label = "Bar chart") {
  if (!data.length) return `${label}: no data.`;
  const { high, low } = extremes(data, (d) => d.value);
  return (
    `${label}, ${data.length} ${data.length === 1 ? "bar" : "bars"}. Highest: ${high.label}, ${formatValue(high.value)}. ` +
    `Lowest: ${low.label}, ${formatValue(low.value)}.`
  );
}

export function forecastSummary(series) {
  const actual = series.filter((p) => p.actual !== null);
  const forecast = series.filter((p) => p.forecast !== null);
  if (!actual.length || !forecast.length) return "Forecast chart: no data.";
  const last = actual[actual.length - 1];
  const values = forecast.map((p) => p.forecast);
  return (
    `Line chart of actual units sold for ${actual.length} weeks, followed by a ${forecast.length}-week forecast. ` +
    `Last actual week (${last.label}): ${formatNumber(last.actual)} units. ` +
    `Forecast: ${formatNumber(Math.min(...values), 0)} to ${formatNumber(Math.max(...values), 0)} units per week, ` +
    `likely range ${formatNumber(Math.min(...forecast.map((p) => p.lower)), 0)} to ` +
    `${formatNumber(Math.max(...forecast.map((p) => p.upper)), 0)}.`
  );
}
