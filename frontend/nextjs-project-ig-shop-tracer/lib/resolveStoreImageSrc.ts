import type { StoreItem } from "@/components/StoreCard";

const BACKEND_ORIGIN = process.env.BACKEND_BASE_URL;
export const STORE_IMAGE_PLACEHOLDER_SRC =
  "https://dummyimage.com/480x480/e5e7eb/6b7280&text=No+Image";

/** Resolves the display URL for a store logo (local file, proxied remote, or placeholder). */
export function resolveStoreImageSrc(item: StoreItem): string {
  const trimmedLocalLogoPath = item.localLogoPath?.trim() ?? "";
  const trimmedImageUrl = item.imageUrl.trim();
  const hasLocalLogoPath = trimmedLocalLogoPath.length > 0;
  const localLogoAbsoluteUrl = trimmedLocalLogoPath.startsWith("/")
    ? `${BACKEND_ORIGIN}${trimmedLocalLogoPath}`
    : `${BACKEND_ORIGIN}/${trimmedLocalLogoPath}`;
  
  if (hasLocalLogoPath) {
    return localLogoAbsoluteUrl;
  }
  if (trimmedImageUrl.length > 0) {
    return `/api/image-proxy?url=${encodeURIComponent(trimmedImageUrl)}`;
  }
  return STORE_IMAGE_PLACEHOLDER_SRC;
}
