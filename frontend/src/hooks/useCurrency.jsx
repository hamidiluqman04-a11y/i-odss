import { createContext, useContext, useState } from "react";
import { formatMoney } from "../services/format";

export const CURRENCY_SYMBOLS = ["RM", "Rp", "₱", "S$", "฿", "$"];
const STORAGE_KEY = "iodss.currency";
const CurrencyContext = createContext(null);

function readStored() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return CURRENCY_SYMBOLS.includes(value) ? value : "RM";
  } catch {
    return "RM";
  }
}

/**
 * The currency SYMBOL shown next to money values. It only changes the label;
 * amounts are shown exactly as they appear in the uploaded file (no conversion).
 */
export function CurrencyProvider({ children }) {
  const [symbol, setSymbolState] = useState(readStored);
  const setSymbol = (value) => {
    setSymbolState(value);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* convenience only */
    }
  };
  const money = (value) => formatMoney(value, symbol);
  return <CurrencyContext.Provider value={{ symbol, setSymbol, money }}>{children}</CurrencyContext.Provider>;
}

export function useCurrency() {
  return useContext(CurrencyContext);
}
