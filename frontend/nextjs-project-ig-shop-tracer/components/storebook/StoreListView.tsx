"use client";

/**
 * StoreListView
 *
 * Renders the store collection in grid and map views. Both stay mounted after the
 * map is first opened so switching views does not reload the Google Map instance.
 */

import { useMemo, useRef } from "react";
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
  const mapActivatedRef = useRef(false);
  const isMapVisible = viewMode === "map";
  if (isMapVisible) {
    mapActivatedRef.current = true;
  }
  const mapEverActivated = mapActivatedRef.current;

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
    <div className="min-w-0 px-3 pb-28 pt-2 sm:px-6 sm:pb-32">
      {isLoading ? (
        <p className="rounded-2xl bg-zinc-50 px-4 py-6 text-sm text-zinc-600 ring-1 ring-zinc-200">
          Loading stores...
        </p>
      ) : null}
      {error ? (
        <p className="mt-3 break-words rounded-2xl bg-red-50 px-4 py-6 text-sm text-red-700 ring-1 ring-red-200">
          {error}
        </p>
      ) : null}

      {isFavoriteListEmpty ? (
        <div
          className="relative mt-4 overflow-hidden rounded-3xl bg-gradient-to-br from-[#fce7f3] via-[#faf5ff] to-[#e0e7ff] px-4 py-10 text-center shadow-[0_20px_60px_-15px_rgba(219,39,119,0.35)] ring-2 ring-white/80 sm:px-6 sm:py-14"
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
          <p className="relative text-xl font-black tracking-tight text-zinc-900 sm:text-3xl">
            <span className="bg-gradient-to-r from-[#f97316] via-[#e11d48] to-[#7c3aed] bg-clip-text text-transparent drop-shadow-sm">
              Un-oh!
            </span>{" "}
            <span className="text-zinc-800">
              You don&apos;t have any favorite store yet ;(
            </span>
          </p>
          <p className="relative mt-3 break-words text-sm font-medium text-zinc-600 sm:text-base">
            Tap the{" "}
            <span className="font-semibold text-zinc-800">+</span> button to add
            your first Instagram store, e.g. wanpotea.hk or skewer.kitchen.
          </p>
        </div>
      ) : null}

      {showSearchNoResults ? (
        <p className="mt-6 rounded-2xl bg-zinc-50 px-4 py-6 text-center text-sm text-zinc-600 ring-1 ring-zinc-200">
          No stores match your search. Try a different name, tag, or location.
        </p>
      ) : null}

      {!isFavoriteListEmpty && !showSearchNoResults ? (
        <>
          <div
            className={
              isMapVisible
                ? "hidden"
                : "mt-4 grid min-w-0 grid-cols-2 gap-2.5 sm:gap-4 md:grid-cols-3 lg:grid-cols-4"
            }
            aria-hidden={isMapVisible}
          >
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

          {mapEverActivated ? (
            <div
              className={
                isMapVisible
                  ? "mt-4 min-w-0 overflow-hidden rounded-2xl bg-zinc-50 p-3 text-zinc-700 ring-1 ring-zinc-200 sm:p-5"
                  : "hidden"
              }
              role="region"
              aria-label="Map view"
              aria-hidden={!isMapVisible}
            >
              <h2 className="text-base font-semibold text-zinc-900 sm:text-lg">
                Store Map View
              </h2>
              <p className="pt-1 text-sm text-zinc-600">
                Tap a marker to open store details.
              </p>
              {isSettingsLoading ? (
                <p className="mt-4 text-sm text-zinc-600">Loading map settings...</p>
              ) : settingsError ? (
                <p className="mt-4 break-words text-sm text-red-700">
                  Unable to load map settings. {settingsError}
                </p>
              ) : (
                <>
                  <StoreLocationsMap
                    className="mt-4"
                    apiKey={googleMapsApiKey}
                    locations={mapLocations}
                    onLocationSelect={handleMapLocationSelect}
                    isVisible={isMapVisible}
                  />
                  <p className="mt-3 rounded-xl border border-amber-300/90 bg-gradient-to-r from-amber-50 via-orange-50 to-amber-50 px-3 py-2.5 text-center text-xs font-semibold leading-relaxed text-amber-950 shadow-sm ring-1 ring-amber-200/60 sm:text-sm">
                    <span className="text-base font-black text-amber-600 sm:text-lg">
                      *
                    </span>{" "}
                    Map location markers are shown on a best-effort basis and
                    may not include every store address listed in store details.
                  </p>
                </>
              )}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
