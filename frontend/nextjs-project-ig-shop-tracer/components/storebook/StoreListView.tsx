"use client";

/**
 * StoreListView
 *
 * Renders the store collection in either grid or map-placeholder view. Also
 * handles the lightweight loading and error banners. This is the main content
 * that lives inside the storebook scroll container.
 */

import { useMemo } from "react";
import StoreCard, { type StoreItem, type StoreLocation } from "@/components/StoreCard";
import StoreLocationsMap, {
  type MapLocation,
} from "@/components/storebook/StoreLocationsMap";
import type { ViewMode } from "@/components/StorebookHeader";
import { isWithinHongKong } from "@/lib/hongKongBounds";

function isUsableHongKongBranchLocation({
  latitude,
  longitude,
}: StoreLocation): boolean {
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return false;
  }
  if (latitude === 0 && longitude === 0) {
    return false;
  }
  return isWithinHongKong(latitude, longitude);
}

type StoreListViewProps = {
  viewMode: ViewMode;
  stores: StoreItem[];
  isLoading: boolean;
  error: string | null;
  googleMapsApiKey: string;
  isSettingsLoading?: boolean;
  settingsError?: string | null;
  /** True when bookmarks loaded successfully but the list has no stores yet. */
  isFavoriteListEmpty: boolean;
  /** True when the user has at least one bookmark (before search filter). */
  hasBookmarks: boolean;
  isDeleteMode?: boolean;
  onStoreSelect?: (item: StoreItem) => void;
  onDeleteStore?: (item: StoreItem) => void;
  deletingStoreObjectId?: string | null;
};

export default function StoreListView({
  viewMode,
  stores,
  isLoading,
  error,
  googleMapsApiKey,
  isSettingsLoading = false,
  settingsError = null,
  isFavoriteListEmpty,
  hasBookmarks,
  isDeleteMode = false,
  onStoreSelect,
  onDeleteStore,
  deletingStoreObjectId = null,
}: StoreListViewProps) {
  const showSearchNoResults =
    !isLoading && !error && hasBookmarks && stores.length === 0;

  const mapLocations = useMemo<MapLocation[]>(
    () =>
      stores.flatMap((item) => {
        const label = item.fullName || item.username;
        return item.storeLocations
          .filter(isUsableHongKongBranchLocation)
          .map((location, index) => ({
            id: `${item.id}:${index}:${location.latitude}:${location.longitude}`,
            storeId: item.id,
            latitude: location.latitude,
            longitude: location.longitude,
            label,
          }));
      }),
    [stores],
  );

  const handleMapLocationSelect = (location: MapLocation) => {
    const matchedStore = stores.find((item) => item.id === location.storeId);
    if (matchedStore) {
      onStoreSelect?.(matchedStore);
    }
  };

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

      {isFavoriteListEmpty ? (
        <div
          className="relative mt-4 overflow-hidden rounded-3xl bg-gradient-to-br from-[#fce7f3] via-[#faf5ff] to-[#e0e7ff] px-6 py-14 text-center shadow-[0_20px_60px_-15px_rgba(219,39,119,0.35)] ring-2 ring-white/80"
          role="status"
          aria-live="polite"
        >
          <div
            className="pointer-events-none absolute -left-16 -top-16 h-40 w-40 rounded-full bg-[#f97316]/25 blur-3xl"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute -bottom-12 -right-12 h-44 w-44 rounded-full bg-[#a855f7]/30 blur-3xl"
            aria-hidden
          />
          <p className="relative text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl">
            <span className="bg-gradient-to-r from-[#f97316] via-[#e11d48] to-[#7c3aed] bg-clip-text text-transparent drop-shadow-sm">
              Un-oh!
            </span>{" "}
            <span className="text-zinc-800">
              You don&apos;t have any favorite store yet ;(
            </span>
          </p>
          <p className="relative mt-3 text-sm font-medium text-zinc-600 sm:text-base">
            Tap the{" "}
            <span className="font-semibold text-zinc-800">+</span> button to add
            your first Instagram shop.
          </p>
        </div>
      ) : null}

      {showSearchNoResults ? (
        <p className="mt-6 rounded-2xl bg-zinc-50 px-4 py-6 text-center text-sm text-zinc-600 ring-1 ring-zinc-200">
          No stores match your search. Try a different name.
        </p>
      ) : null}

      {!isFavoriteListEmpty && !showSearchNoResults ? (
        viewMode === "grid" ? (
          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
            {stores.map((item) => (
              <StoreCard
                key={item.id}
                item={item}
                onSelect={onStoreSelect}
                onDelete={isDeleteMode ? onDeleteStore : undefined}
                isDeleting={deletingStoreObjectId === item.objectId}
              />
            ))}
          </div>
        ) : (
          <div
            className="mt-4 rounded-2xl bg-zinc-50 p-5 text-zinc-700 ring-1 ring-zinc-200"
            role="region"
            aria-label="Map view"
          >
            <h2 className="text-lg font-semibold text-zinc-900">
              Store Map View
            </h2>
            <p className="pt-1 text-sm text-zinc-600">
              Tap a marker to open store details.
            </p>
            {isSettingsLoading ? (
              <p className="mt-4 text-sm text-zinc-600">Loading map settings...</p>
            ) : settingsError ? (
              <p className="mt-4 text-sm text-red-700">
                Unable to load map settings. {settingsError}
              </p>
            ) : (
              <StoreLocationsMap
                className="mt-4"
                apiKey={googleMapsApiKey}
                locations={mapLocations}
                onLocationSelect={handleMapLocationSelect}
              />
            )}
          </div>
        )
      ) : null}
    </div>
  );
}
