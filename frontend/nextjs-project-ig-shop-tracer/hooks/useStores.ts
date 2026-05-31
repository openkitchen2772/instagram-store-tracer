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

const GET_BOOKMARKS_API_BASE_URL = "/api/backend/get_bookmarks";
const ADD_STORE_API_URL = "/api/backend/add_store";
const DELETE_STORE_API_URL = "/api/backend/delete_store";
const GET_STORE_PROFILE_API_BASE_URL = "/api/backend/get_store_profile";

type StoreItemApi = {
  id?: string;
  objectId?: string;
  username?: string;
  fullName?: string;
  imageUrl?: string;
  localLogoPath?: string;
  latitude?: number;
  longitude?: number;
  description?: string;
  tags?: string[];
  storeLocations?: [number, number][];
  addresses?: string[];
};

function mapStoreLocations(
  storeLocations: StoreItemApi["storeLocations"],
): StoreItem["storeLocations"] {
  if (!storeLocations?.length) {
    return [];
  }

  return storeLocations
    .map(([latitude, longitude]) => ({
      latitude: Number(latitude),
      longitude: Number(longitude),
    }))
    .filter(
      ({ latitude, longitude }) =>
        Number.isFinite(latitude) && Number.isFinite(longitude),
    );
}

type GetBookmarksResponse = {
  success?: boolean;
  message?: string;
  data?: {
    uuid?: string;
    stores?: StoreItemApi[];
  };
};

export type SubmitStoreResult = { ok: true } | { ok: false; error: string };
export type DeleteStoreResult = { ok: true } | { ok: false; error: string };
export type GetStoreProfileResult = { ok: true } | { ok: false; error: string };

export type UseStoresResult = {
  stores: StoreItem[];
  isLoading: boolean;
  error: string | null;
  /** Re-fetch the store list. */
  reload: () => Promise<void>;
  /** Submit a new store and, on success, refresh the list. */
  submitStore: (username: string) => Promise<SubmitStoreResult>;
  /** Remove a bookmarked store and, on success, refresh the list. */
  deleteStore: (objectId: string) => Promise<DeleteStoreResult>;
  /** Retrieve the latest fields for one store by username. */
  getStoreProfile: (username: string) => Promise<GetStoreProfileResult>;
};

export function useStores(bookmarksUuid: string | null): UseStoresResult {
  const [stores, setStores] = useState<StoreItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!bookmarksUuid?.trim()) {
      setStores([]);
      setError(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${GET_BOOKMARKS_API_BASE_URL}/${encodeURIComponent(bookmarksUuid)}`,
        {
          method: "GET",
          signal,
        },
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch bookmarks (HTTP ${response.status})`);
      }

      const payload = (await response.json()) as GetBookmarksResponse;
      if (!payload.success) {
        throw new Error(payload.message || "Failed to fetch bookmarks");
      }

      const bookmarkStores = payload.data?.stores ?? [];
      const mappedStores: StoreItem[] = bookmarkStores.map((item) => ({
        id: item.id ?? "",
        objectId: item.objectId ?? "",
        username: item.username ?? "",
        fullName: item.fullName ?? "",
        imageUrl: item.imageUrl ?? "",
        localLogoPath: item.localLogoPath ?? "",
        latitude: item.latitude ?? 0,
        longitude: item.longitude ?? 0,
        description: item.description ?? "",
        tags: item.tags ?? [],
        storeLocations: mapStoreLocations(item.storeLocations),
        addresses: (item.addresses ?? []).filter((address) => address.trim().length > 0),
      }));
      setStores(mappedStores);
    } catch (err) {
      if (signal?.aborted) return;
      const message =
        err instanceof Error ? err.message : "Failed to fetch bookmarks";
      setError(message);
    } finally {
      if (!signal?.aborted) {
        setIsLoading(false);
      }
    }
  }, [bookmarksUuid]);

  const reload = useCallback(() => load(), [load]);

  const submitStore = useCallback(
    async (username: string): Promise<SubmitStoreResult> => {
      const normalizedUuid = bookmarksUuid?.trim() ?? "";
      if (!normalizedUuid) {
        const missingSessionMessage = "Missing bookmarks session id";
        setError(missingSessionMessage);
        return { ok: false, error: missingSessionMessage };
      }
      setError(null);
      try {
        const response = await fetch(ADD_STORE_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, uuid: normalizedUuid }),
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
    [bookmarksUuid, load],
  );

  const deleteStore = useCallback(
    async (objectId: string): Promise<DeleteStoreResult> => {
      const normalizedUuid = bookmarksUuid?.trim() ?? "";
      const normalizedObjectId = objectId.trim();
      if (!normalizedUuid) {
        const missingSessionMessage = "Missing bookmarks session id";
        setError(missingSessionMessage);
        return { ok: false, error: missingSessionMessage };
      }
      if (!normalizedObjectId) {
        const missingStoreMessage = "Missing store object id";
        setError(missingStoreMessage);
        return { ok: false, error: missingStoreMessage };
      }
      setError(null);
      try {
        const response = await fetch(DELETE_STORE_API_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            uuid: normalizedUuid,
            store_id: normalizedObjectId,
          }),
        });

        const body = (await response.json()) as {
          success?: boolean;
          message?: string;
        };

        if (!response.ok || !body.success) {
          throw new Error(
            body.message || `Failed to delete store (HTTP ${response.status})`,
          );
        }

        await load();
        return { ok: true };
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to delete store";
        setError(message);
        return { ok: false, error: message };
      }
    },
    [bookmarksUuid, load],
  );

  const getStoreProfile = useCallback(
    async (username: string): Promise<GetStoreProfileResult> => {
      const normalizedUsername = username.trim().replace(/^@+/, "");
      if (!normalizedUsername) {
        const missingUsernameMessage = "Username is required";
        setError(missingUsernameMessage);
        return { ok: false, error: missingUsernameMessage };
      }

      setError(null);
      try {
        const response = await fetch(
          `${GET_STORE_PROFILE_API_BASE_URL}/${encodeURIComponent(normalizedUsername)}`,
          { method: "GET" },
        );

        const body = (await response.json()) as StoreItemApi & { detail?: string };
        if (!response.ok) {
          throw new Error(
            body.detail || `Failed to fetch store profile (HTTP ${response.status})`,
          );
        }

        const mappedStore: StoreItem = {
          id: body.id ?? "",
          objectId: body.objectId ?? "",
          username: body.username ?? "",
          fullName: body.fullName ?? "",
          imageUrl: body.imageUrl ?? "",
          localLogoPath: body.localLogoPath ?? "",
          latitude: body.latitude ?? 0,
          longitude: body.longitude ?? 0,
          description: body.description ?? "",
          tags: body.tags ?? [],
          storeLocations: mapStoreLocations(body.storeLocations),
          addresses: (body.addresses ?? []).filter((address) => address.trim().length > 0),
        };
        const hasGeneratedTags = mappedStore.tags.some((tag) => tag.trim().length > 0);
        if (hasGeneratedTags) {
          setStores((currentStores) =>
            currentStores.map((storeItem) =>
              storeItem.username.trim().toLowerCase() === normalizedUsername.toLowerCase()
                ? mappedStore
                : storeItem,
            ),
          );
        }
        return { ok: true };
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to fetch store profile";
        setError(message);
        return { ok: false, error: message };
      }
    },
    [],
  );

  useEffect(() => {
    const controller = new AbortController();
    // Mount-time data fetch is a legitimate external sync: we are subscribing
    // to the backend rather than mirroring derivable state. The setState calls
    // inside `load` are required to surface loading/error to the UI.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(controller.signal);

    return () => {
      controller.abort();
    };
  }, [load]);

  return { stores, isLoading, error, reload, submitStore, deleteStore, getStoreProfile };
}
