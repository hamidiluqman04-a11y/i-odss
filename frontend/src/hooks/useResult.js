import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { useDatasets } from "./useDatasets";

/**
 * Loads one saved analysis ("dashboard", "forecast", ...) for the dataset
 * chosen in the top bar, and reloads when the user picks another dataset.
 * Answers that arrive after the user switched datasets are ignored.
 */
export function useResult(kind) {
  const { current } = useDatasets();
  const datasetId = current?.id ?? null;
  const [state, setState] = useState({ status: "idle", data: null, error: null });
  const latest = useRef(0);

  const load = useCallback(async () => {
    if (!datasetId) return;
    const request = ++latest.current;
    setState((s) => ({ ...s, status: "loading", error: null }));
    try {
      const data = await api.getResult(datasetId, kind);
      if (request === latest.current) setState({ status: "ready", data, error: null });
    } catch (error) {
      if (request === latest.current) setState({ status: "error", data: null, error });
    }
  }, [datasetId, kind]);

  useEffect(() => {
    if (datasetId) load();
    else setState({ status: "idle", data: null, error: null });
  }, [datasetId, load]);

  return { ...state, reload: load };
}
