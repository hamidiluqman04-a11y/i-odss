import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "../services/api";

const DatasetContext = createContext(null);
const STORAGE_KEY = "iodss.currentDataset";

function readStoredId() {
  try {
    const value = Number(localStorage.getItem(STORAGE_KEY));
    return Number.isInteger(value) && value > 0 ? value : null;
  } catch {
    return null; // storage can be blocked (private window); just start fresh
  }
}

function storeId(id) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, String(id));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* remembering the choice is only a convenience */
  }
}

/**
 * The logged-in user's uploaded datasets and which one is being viewed.
 * The chosen dataset id is remembered in this browser only.
 */
export function DatasetProvider({ children }) {
  const [datasets, setDatasets] = useState([]);
  const [currentId, setCurrentId] = useState(readStoredId);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setStatus((s) => (s === "ready" ? s : "loading"));
    try {
      const { datasets } = await api.listDatasets();
      setDatasets(datasets);
      setCurrentId((id) => {
        const next = datasets.some((d) => d.id === id) ? id : (datasets[0]?.id ?? null);
        storeId(next);
        return next;
      });
      setStatus("ready");
    } catch (err) {
      setError(err);
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const select = (id) => {
    setCurrentId(id);
    storeId(id);
  };

  const added = (dataset) => {
    setDatasets((list) => [dataset, ...list]);
    select(dataset.id);
  };

  const remove = async (id) => {
    await api.deleteDataset(id);
    const rest = datasets.filter((d) => d.id !== id);
    setDatasets(rest);
    if (currentId === id) select(rest[0]?.id ?? null);
  };

  const current = datasets.find((d) => d.id === currentId) ?? null;

  return (
    <DatasetContext.Provider value={{ datasets, current, status, error, refresh, select, added, remove }}>
      {children}
    </DatasetContext.Provider>
  );
}

export function useDatasets() {
  return useContext(DatasetContext);
}
