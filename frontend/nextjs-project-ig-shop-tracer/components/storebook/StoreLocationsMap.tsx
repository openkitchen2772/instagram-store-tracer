"use client";

/**
 * StoreLocationsMap
 *
 * Loads the Google Maps JavaScript API once and keeps the map instance mounted.
 * Marker updates run when locations change; resize runs when the map becomes visible
 * again after being hidden (e.g. grid/map view toggle).
 * The user's current position is shown when browser geolocation is allowed.
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
  /** When false, the map stays mounted but hidden; a resize is triggered when true. */
  isVisible?: boolean;
};

type GeolocationStatus = "idle" | "watching" | "ready" | "denied" | "unavailable";

function isValidCoordinate(value: number): boolean {
  return Number.isFinite(value);
}

function hasUsableCoordinates(location: MapLocation): boolean {
  return (
    isValidCoordinate(location.latitude) &&
    isValidCoordinate(location.longitude)
  );
}

function fitMapToVisiblePoints(
  map: google.maps.Map,
  storeMarkers: google.maps.Marker[],
  userPosition: google.maps.LatLngLiteral | null,
): void {
  const bounds = new google.maps.LatLngBounds();
  let pointCount = 0;

  storeMarkers.forEach((marker) => {
    const position = marker.getPosition();
    if (position) {
      bounds.extend(position);
      pointCount += 1;
    }
  });

  if (userPosition) {
    bounds.extend(userPosition);
    pointCount += 1;
  }

  if (pointCount === 0) {
    return;
  }

  if (pointCount === 1) {
    map.setCenter(bounds.getCenter());
    map.setZoom(userPosition && storeMarkers.length === 0 ? 14 : 12);
    return;
  }

  map.fitBounds(bounds, 64);
}

function geolocationErrorMessage(error: GeolocationPositionError): string {
  if (error.code === error.PERMISSION_DENIED) {
    return "Location permission denied. Enable location access to see your position on the map.";
  }
  if (error.code === error.POSITION_UNAVAILABLE) {
    return "Your location is temporarily unavailable.";
  }
  return "Timed out while fetching your location.";
}

export default function StoreLocationsMap({
  apiKey,
  locations,
  onLocationSelect,
  className = "",
  isVisible = true,
}: StoreLocationsMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const mapsApiRef = useRef<typeof google.maps | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const userMarkerRef = useRef<google.maps.Marker | null>(null);
  const userPositionRef = useRef<google.maps.LatLngLiteral | null>(null);
  const onLocationSelectRef = useRef(onLocationSelect);
  const [mapStatus, setMapStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [mapError, setMapError] = useState<string | null>(null);
  const [geolocationStatus, setGeolocationStatus] =
    useState<GeolocationStatus>("idle");
  const [geolocationHint, setGeolocationHint] = useState<string | null>(null);

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

  const refitMapBounds = () => {
    const map = mapRef.current;
    if (!map) {
      return;
    }
    fitMapToVisiblePoints(map, markersRef.current, userPositionRef.current);
  };

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

        mapsApiRef.current = mapsApi;
        const map = new mapsApi.Map(mapContainerRef.current, {
          center: { lat: 22.3193, lng: 114.1694 },
          zoom: 11,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
        });
        mapRef.current = map;
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
      userMarkerRef.current?.setMap(null);
      userMarkerRef.current = null;
      userPositionRef.current = null;
      mapRef.current = null;
      mapsApiRef.current = null;
    };
  }, [trimmedApiKey]);

  useEffect(() => {
    const map = mapRef.current;
    const mapsApi = mapsApiRef.current;
    if (!map || !mapsApi || mapStatus !== "ready") {
      return;
    }

    markersRef.current.forEach((marker) => marker.setMap(null));
    markersRef.current = [];

    markersRef.current = usableLocations.map((location) => {
      const position = {
        lat: location.latitude,
        lng: location.longitude,
      };

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

    refitMapBounds();
  }, [locationsKey, mapStatus, usableLocations]);

  useEffect(() => {
    const map = mapRef.current;
    if (!isVisible || !map) {
      return;
    }

    google.maps.event.trigger(map, "resize");
    refitMapBounds();
  }, [isVisible]);

  useEffect(() => {
    if (mapStatus !== "ready" || !isVisible) {
      return;
    }

    if (!navigator.geolocation) {
      setGeolocationStatus("unavailable");
      setGeolocationHint("Geolocation is not supported in this browser.");
      return;
    }

    setGeolocationStatus("watching");
    setGeolocationHint(null);

    const syncUserMarker = (position: GeolocationPosition) => {
      const latitude = position.coords.latitude;
      const longitude = position.coords.longitude;
      if (!isValidCoordinate(latitude) || !isValidCoordinate(longitude)) {
        return;
      }

      const userPosition = { lat: latitude, lng: longitude };
      userPositionRef.current = userPosition;

      const map = mapRef.current;
      const mapsApi = mapsApiRef.current;
      if (!map || !mapsApi) {
        return;
      }

      if (!userMarkerRef.current) {
        userMarkerRef.current = new mapsApi.Marker({
          map,
          position: userPosition,
          title: "Your location",
          zIndex: 1000,
          icon: {
            path: mapsApi.SymbolPath.CIRCLE,
            scale: 9,
            fillColor: "#2563eb",
            fillOpacity: 1,
            strokeColor: "#ffffff",
            strokeWeight: 2,
          },
        });
      } else {
        userMarkerRef.current.setPosition(userPosition);
      }

      setGeolocationStatus("ready");
      setGeolocationHint(null);
    };

    const handleGeolocationError = (error: GeolocationPositionError) => {
      setGeolocationStatus(error.code === error.PERMISSION_DENIED ? "denied" : "unavailable");
      setGeolocationHint(geolocationErrorMessage(error));
      userMarkerRef.current?.setMap(null);
      userMarkerRef.current = null;
      userPositionRef.current = null;
    };

    const watchId = navigator.geolocation.watchPosition(
      syncUserMarker,
      handleGeolocationError,
      {
        enableHighAccuracy: true,
        maximumAge: 30_000,
        timeout: 15_000,
      },
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
      userMarkerRef.current?.setMap(null);
      userMarkerRef.current = null;
      userPositionRef.current = null;
      setGeolocationStatus("idle");
      setGeolocationHint(null);
    };
  }, [isVisible, mapStatus]);

  if (!trimmedApiKey) {
    return (
      <div className={`min-w-0 ${className}`}>
        <div
          className="flex h-[min(280px,45dvh)] w-full min-w-0 items-center justify-center rounded-xl bg-zinc-100 px-4 text-center text-sm text-zinc-600 ring-1 ring-zinc-200 sm:h-[min(420px,55dvh)]"
          role="status"
        >
          Google Maps API key is not configured.
        </div>
      </div>
    );
  }

  return (
    <div className={`min-w-0 ${className}`}>
      <div
        ref={mapContainerRef}
        className="h-[min(280px,45dvh)] w-full min-w-0 overflow-hidden rounded-xl bg-zinc-100 ring-1 ring-zinc-200 sm:h-[min(420px,55dvh)]"
        role="application"
        aria-label="Store locations map"
      />
      {mapStatus === "loading" ? (
        <p className="mt-2 break-words text-sm text-zinc-600">Loading map...</p>
      ) : null}
      {mapStatus === "error" && mapError ? (
        <p className="mt-2 break-words text-sm text-red-700">{mapError}</p>
      ) : null}
      {mapStatus === "ready" && geolocationStatus === "watching" ? (
        <p className="mt-2 text-sm text-zinc-600">Finding your location...</p>
      ) : null}
      {mapStatus === "ready" && geolocationHint ? (
        <p className="mt-2 break-words text-sm text-zinc-600">{geolocationHint}</p>
      ) : null}
      {mapStatus === "ready" && usableLocations.length === 0 ? (
        <p className="mt-2 text-sm text-zinc-600">
          {geolocationStatus === "ready"
            ? "No store branches with Hong Kong locations to display. Your location is shown on the map."
            : "No store branches with Hong Kong locations to display on the map."}
        </p>
      ) : null}
    </div>
  );
}
