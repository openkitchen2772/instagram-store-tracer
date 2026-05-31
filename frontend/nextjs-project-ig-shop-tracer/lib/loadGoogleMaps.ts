import { importLibrary, setOptions } from "@googlemaps/js-api-loader";

let mapsOptionsConfigured = false;

/**
 * Configures and loads the Maps JavaScript API. setOptions() is called at most
 * once per page load (required by @googlemaps/js-api-loader v2).
 */
export async function loadGoogleMaps(apiKey: string): Promise<typeof google.maps> {
  const trimmedKey = apiKey.trim();
  if (!trimmedKey) {
    throw new Error("Google Maps API key is not configured.");
  }

  if (!mapsOptionsConfigured) {
    setOptions({ key: trimmedKey, v: "weekly" });
    mapsOptionsConfigured = true;
  }

  await importLibrary("maps");
  return google.maps;
}
