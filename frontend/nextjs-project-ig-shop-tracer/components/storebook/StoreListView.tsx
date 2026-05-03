"use client";

/**
 * StoreListView
 *
 * Renders the store collection in either grid or map-placeholder view. Also
 * handles the lightweight loading and error banners. This is the main content
 * that lives inside the storebook scroll container.
 */

import StoreCard, { type StoreItem } from "@/components/StoreCard";
import type { ViewMode } from "@/components/StorebookHeader";

type StoreListViewProps = {
  viewMode: ViewMode;
  stores: StoreItem[];
  isLoading: boolean;
  error: string | null;
};

export default function StoreListView({
  viewMode,
  stores,
  isLoading,
  error,
}: StoreListViewProps) {
  return (
    <div className="px-4 pb-28 pt-2 sm:px-6 sm:pb-32">
      {isLoading ? (
        <p className="rounded-2xl bg-zinc-50 px-4 py-6 text-sm text-zinc-600 ring-1 ring-zinc-200">
          Loading stores...
        </p>
      ) : null}
      {error ? (
        <p className="mt-3 rounded-2xl bg-red-50 px-4 py-6 text-sm text-red-700 ring-1 ring-red-200">
          Unable to load stores. {error}
        </p>
      ) : null}

      {viewMode === "grid" ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
          {stores.map((item) => (
            <StoreCard key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <div
          className="rounded-2xl bg-zinc-50 p-5 text-zinc-700 ring-1 ring-zinc-200"
          role="region"
          aria-label="Map view"
        >
          <h2 className="text-lg font-semibold text-zinc-900">Store Map View</h2>
          <p className="pt-1 text-sm text-zinc-600">
            Basic map placeholder with store coordinates.
          </p>
          <ul className="mt-4 grid gap-2 text-sm">
            {stores.map((item) => (
              <li
                key={item.id}
                className="rounded-xl bg-white px-3 py-2 ring-1 ring-zinc-200"
              >
                {item.name}: ({item.latitude}, {item.longitude})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
