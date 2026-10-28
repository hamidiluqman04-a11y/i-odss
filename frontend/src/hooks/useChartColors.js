import { useState } from "react";

// Chart roles defined in styles.css, all mapped onto DESIGN.md colours.
const TOKENS = ["chart-actual", "chart-forecast", "chart-band", "chart-bar", "chart-grid", "chart-axis", "body", "canvas"];

function read() {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(TOKENS.map((t) => [t, style.getPropertyValue(`--${t}`).trim()]));
}

/**
 * Recharts draws SVG with colour attributes, which cannot use CSS variables
 * directly, so this hook reads the colour tokens from styles.css once.
 */
export function useChartColors() {
  const [colors] = useState(read);
  return colors;
}
