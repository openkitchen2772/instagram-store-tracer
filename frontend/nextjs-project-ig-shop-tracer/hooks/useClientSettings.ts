"use client";

/**
 * useClientSettings
 *
 * Fetches public client settings from the backend on initial mount (e.g.
 * Google Maps API key). Aborts in-flight requests on unmount.
 */

import { useCallback, useEffect, useState } from "react";

const CLIENT_SETTINGS_API_URL = "/api/backend/settings";

type ClientSettingsApi = {
  googleMapsApiKey?: string;
};

export type UseClientSettingsResult = {
  googleMapsApiKey: string;
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
};

export function useClientSettings(): UseClientSettingsResult {
  const [googleMapsApiKey, setGoogleMapsApiKey] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(CLIENT_SETTINGS_API_URL, {
        method: "GET",
        signal,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch settings (HTTP ${response.status})`);
      }

      const payload = (await response.json()) as ClientSettingsApi;
      setGoogleMapsApiKey(payload.googleMapsApiKey?.trim() ?? "");
    } catch (err) {
      if (signal?.aborted) return;
      const message =
        err instanceof Error ? err.message : "Failed to fetch settings";
      setError(message);
      setGoogleMapsApiKey("");
    } finally {
      if (!signal?.aborted) {
        setIsLoading(false);
      }
    }
  }, []);

  const reload = useCallback(() => load(), [load]);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(controller.signal);

    return () => {
      controller.abort();
    };
  }, [load]);

  return { googleMapsApiKey, isLoading, error, reload };
}
