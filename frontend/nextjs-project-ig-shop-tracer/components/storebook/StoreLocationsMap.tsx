"use client";

/**
 * StoreLocationsMap
 *
 * Loads the Google Maps JavaScript API with the provided key and renders a
 * map with one marker per location. Fits bounds when multiple stores exist.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { loadGoogleMaps } from "@/lib/loadGoogleMaps";

export type MapLocation = {
  id: string;
  storeId: string;
  latitude: number;
  longitude: number;
  label?: string;
};

type StoreLocationsMapProps = {
  apiKey: string;
  locations: MapLocation[];
  onLocationSelect?: (location: MapLocation) => void;
  className?: string;
};

function isValidCoordinate(value: number): boolean {
  return Number.isFinite(value);
}

function hasUsableCoordinates(location: MapLocation): boolean {
  return (
    isValidCoordinate(location.latitude) &&
    isValidCoordinate(location.longitude)
  );
}

export default function StoreLocationsMap({
  apiKey,
  locations,
  onLocationSelect,
  className = "",
}: StoreLocationsMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const onLocationSelectRef = useRef(onLocationSelect);
  const [mapStatus, setMapStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [mapError, setMapError] = useState<string | null>(null);

  const usableLocations = useMemo(
    () => locations.filter(hasUsableCoordinates),
    [locations],
  );

  const locationsKey = useMemo(
    () =>
      usableLocations
        .map(
          (location) =>
            `${location.id}:${location.latitude}:${location.longitude}:${location.label ?? ""}`,
        )
        .join("|"),
    [usableLocations],
  );

  useEffect(() => {
    onLocationSelectRef.current = onLocationSelect;
  }, [onLocationSelect]);

  const trimmedApiKey = apiKey.trim();

  useEffect(() => {
    if (!trimmedApiKey || !mapContainerRef.current) {
      return;
    }

    let isCancelled = false;
    setMapStatus("loading");
    setMapError(null);

    void (async () => {
      try {
        const mapsApi = await loadGoogleMaps(trimmedApiKey);
        if (isCancelled || !mapContainerRef.current) {
          return;
        }

        const defaultCenter = { lat: 0, lng: 0 };
        const map = new mapsApi.Map(mapContainerRef.current, {
          center: defaultCenter,
          zoom: 2,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
        });
        mapRef.current = map;

        markersRef.current.forEach((marker) => marker.setMap(null));
        markersRef.current = [];

        if (usableLocations.length === 0) {
          setMapStatus("ready");
          return;
        }

        const bounds = new mapsApi.LatLngBounds();
        markersRef.current = usableLocations.map((location) => {
          const position = {
            lat: location.latitude,
            lng: location.longitude,
          };
          bounds.extend(position);

          const marker = new mapsApi.Marker({
            map,
            position,
            title: location.label?.trim() || location.id,
          });

          marker.addListener("click", () => {
            onLocationSelectRef.current?.(location);
          });

          return marker;
        });

        if (usableLocations.length === 1) {
          map.setCenter(bounds.getCenter());
          map.setZoom(12);
        } else {
          map.fitBounds(bounds, 64);
        }

        setMapStatus("ready");
      } catch (error) {
        if (isCancelled) {
          return;
        }
        const message =
          error instanceof Error
            ? error.message
            : "Failed to load Google Maps.";
        setMapError(message);
        setMapStatus("error");
      }
    })();

    return () => {
      isCancelled = true;
      markersRef.current.forEach((marker) => marker.setMap(null));
      markersRef.current = [];
      mapRef.current = null;
    };
  }, [trimmedApiKey, locationsKey, usableLocations]);

  if (!trimmedApiKey) {
    return (
      <div className={className}>
        <div
          className="flex h-[min(420px,55dvh)] w-full items-center justify-center rounded-xl bg-zinc-100 px-4 text-center text-sm text-zinc-600 ring-1 ring-zinc-200"
          role="status"
        >
          Google Maps API key is not configured.
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <div
        ref={mapContainerRef}
        className="h-[min(420px,55dvh)] w-full rounded-xl bg-zinc-100 ring-1 ring-zinc-200"
        role="application"
        aria-label="Store locations map"
      />
      {mapStatus === "loading" ? (
        <p className="mt-2 text-sm text-zinc-600">Loading map...</p>
      ) : null}
      {mapStatus === "error" && mapError ? (
        <p className="mt-2 text-sm text-red-700">{mapError}</p>
      ) : null}
      {mapStatus === "ready" && usableLocations.length === 0 ? (
        <p className="mt-2 text-sm text-zinc-600">
          No store branches with Hong Kong locations to display on the map.
        </p>
      ) : null}
    </div>
  );
}
