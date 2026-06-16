"use client";

import { useState, useEffect } from "react";

/**
 * useState that persists to localStorage.
 *
 * SSR-safe: server and first client render use `initial`, then a useEffect
 * hydrates from localStorage so there's no server/client mismatch.
 *
 * The setter accepts both direct values and functional updates, matching
 * the full Dispatch<SetStateAction<T>> interface.
 */
export function useLocalStorage<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(initial);

  // Hydrate from localStorage after client mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored !== null) setValue(JSON.parse(stored) as T);
    } catch {
      // corrupted entry — fall back to initial
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function set(newValue: T | ((prev: T) => T)) {
    setValue((prev) => {
      const next =
        typeof newValue === "function"
          ? (newValue as (prev: T) => T)(prev)
          : newValue;
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {}
      return next;
    });
  }

  function clear() {
    setValue(initial);
    try {
      localStorage.removeItem(key);
    } catch {}
  }

  return [value, set, clear] as const;
}
