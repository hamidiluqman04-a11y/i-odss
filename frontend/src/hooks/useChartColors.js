import { useEffect, useState } from "react";

const TOKENS = ["series-1", "grid", "axis", "text-muted", "text-secondary", "surface"];

function read() {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(TOKENS.map((t) => [t, style.getPropertyValue(`--${t}`).trim()]));
}

/**
 * Recharts draws SVG with colour attributes, which cannot use CSS variables
 * directly. This hook reads the colour tokens from styles.css and re-reads
 * them when the computer switches between light and dark mode.
 */
export function useChartColors() {
  const [colors, setColors] = useState(read);
  useEffect(() => {
    const query = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!query) return undefined;
    const update = () => setColors(read());
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return colors;
}
