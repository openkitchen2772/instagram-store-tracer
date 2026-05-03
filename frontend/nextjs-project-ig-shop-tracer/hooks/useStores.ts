"use client";

/**
 * useStores
 *
 * Centralizes all store-related network calls (list + add) and the derived
 * loading/error state. Keeping the endpoint URLs here means the rest of the
 * UI stays transport-agnostic.
 *
 * - The initial fetch is aborted on unmount to avoid setting state on an
 *   unmounted component (and to prevent duplicate fetches under React strict
 *   mode's double-invoke behavior).
 * - `submitStore` refreshes the list on success so callers don't need to
 *   chain another `reload()`.
 */

import { useCallback, useEffect, useState } from "react";
import type { StoreItem } from "@/components/StoreCard";

const STORE_API_URL = "http://localhost:8000/stores";
const ADD_STORE_API_URL = "http://localhost:8000/add_store";

export type SubmitStoreResult = { ok: true } | { ok: false; error: string };

export type UseStoresResult = {
  stores: StoreItem[];
  isLoading: boolean;
  error: string | null;
  /** Re-fetch the store list. */
  reload: () => Promise<void>;
  /** Submit a new store and, on success, refresh the list. */
  submitStore: (username: string) => Promise<SubmitStoreResult>;
};

export function useStores(): UseStoresResult {
  const [stores, setStores] = useState<StoreItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(STORE_API_URL, {
        method: "GET",
        signal,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch stores (HTTP ${response.status})`);
      }

      const payload = (await response.json()) as StoreItem[];
      setStores(payload);
    } catch (err) {
      if (signal?.aborted) return;
      const message =
        err instanceof Error ? err.message : "Failed to fetch stores";
      setError(message);
    } finally {
      if (!signal?.aborted) {
        setIsLoading(false);
      }
    }
  }, []);

  const reload = useCallback(() => load(), [load]);

  const submitStore = useCallback(
    async (username: string): Promise<SubmitStoreResult> => {
      setError(null);
      try {
        const response = await fetch(ADD_STORE_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username }),
        });

        const body = (await response.json()) as {
          success?: boolean;
          message?: string;
        };

        if (!response.ok || !body.success) {
          throw new Error(
            body.message || `Failed to submit store (HTTP ${response.status})`,
          );
        }

        await load();
        return { ok: true };
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to submit store";
        setError(message);
        return { ok: false, error: message };
      }
    },
    [load],
  );

  useEffect(() => {
    const controller = new AbortController();
    // Mount-time data fetch is a legitimate external sync: we are subscribing
    // to the backend rather than mirroring derivable state. The setState calls
    // inside `load` are required to surface loading/error to the UI.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return { stores, isLoading, error, reload, submitStore };
}
