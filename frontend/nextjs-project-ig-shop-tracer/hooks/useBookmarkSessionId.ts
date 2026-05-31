"use client";

import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";

const BOOKMARK_UUID_STORAGE_KEY = "bookmark-uuid";
const CREATE_BOOKMARK_API_URL = "/api/backend/create_bookmark";

/**
 * Ensures a bookmarks row exists for this uuid (idempotent if backend reports duplicate).
 */
async function createBookmarksByUUID(uuid: string): Promise<void> {
  const response = await fetch(CREATE_BOOKMARK_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uuid }),
  });

  const body = (await response.json()) as { success?: boolean; message?: string };

  if (response.ok && body.success) {
    return;
  }

  const message = body.message ?? "";
  if (message.includes("Bookmarks already exists")) {
    return;
  }

  console.warn(
    "create_bookmark did not succeed; bookmarks may be missing until retry.",
    message || `HTTP ${response.status}`,
  );
}

/**
 * Stable per-browser session id persisted in localStorage. Reuses an existing
 * value when present; otherwise creates one with `uuid` v4 and
 * stores it under `bookmark-uuid`. On first creation, calls the backend
 * `create_bookmark` API so a matching bookmarks document exists before the
 * session id is exposed to consumers (avoids racing `get_bookmarks`). Returns
 * null only until the client effect runs (SSR and first paint).
 */
export function useBookmarkSessionId(): string | null {
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    // Defer setState so we don't sync-update React from an effect body (eslint
    // react-hooks/set-state-in-effect). Reading localStorage still happens once
    // after paint.
    queueMicrotask(() => {
      void (async () => {
        console.log("getting bookmark session")
        let existing: string | null = null;
        try {
          existing = localStorage.getItem(BOOKMARK_UUID_STORAGE_KEY);
        } catch {
          setSessionId(uuidv4());
          return;
        }

        if (existing?.trim()) {
          setSessionId(existing.trim());
          return;
        }

        const created = uuidv4();
        try {
          localStorage.setItem(BOOKMARK_UUID_STORAGE_KEY, created);
        } catch {
          setSessionId(uuidv4());
          return;
        }

        try {
          console.log("ready to create new bookmark by uuid")
          await createBookmarksByUUID(created);
        } catch (error) {
          console.warn("create_bookmark request error:", error);
        }

        setSessionId(created);
      })();
    });
  }, []);

  return sessionId;
}
