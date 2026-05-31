/** Approximate bounding box for Hong Kong (main territory and outlying islands). */
const HONG_KONG_BOUNDS = {
  minLatitude: 22.153,
  maxLatitude: 22.561,
  minLongitude: 113.826,
  maxLongitude: 114.434,
} as const;

export function isWithinHongKong(latitude: number, longitude: number): boolean {
  return (
    latitude >= HONG_KONG_BOUNDS.minLatitude &&
    latitude <= HONG_KONG_BOUNDS.maxLatitude &&
    longitude >= HONG_KONG_BOUNDS.minLongitude &&
    longitude <= HONG_KONG_BOUNDS.maxLongitude
  );
}
