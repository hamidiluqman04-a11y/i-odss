import { useState } from "react";

/**
 * A card with a chart and an equivalent table. The table view makes every
 * value readable without hovering and without relying on colour.
 * `columns`: [{ key, label, numeric?, format? }]
 */
export default function ChartCard({ title, subtitle, note, columns, rows, children }) {
  const [view, setView] = useState("chart");
  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="small muted">{subtitle}</p>}
        </div>
        <span className="spacer" />
        <div className="toggle" role="group" aria-label={`${title}: view as`}>
          <button type="button" aria-pressed={view === "chart"} onClick={() => setView("chart")}>Chart</button>
          <button type="button" aria-pressed={view === "table"} onClick={() => setView("table")}>Table</button>
        </div>
      </div>
      {view === "chart" ? (
        children
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c.key} className={c.numeric ? "num" : undefined}>{c.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {columns.map((c) => (
                    <td key={c.key} className={c.numeric ? "num" : undefined}>
                      {c.format ? c.format(row[c.key]) : row[c.key]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {note && <p className="small secondary card-note">{note}</p>}
    </section>
  );
}
