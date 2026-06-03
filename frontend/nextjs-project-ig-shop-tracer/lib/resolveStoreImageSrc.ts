import type { StoreItem } from "@/components/StoreCard";

export const STORE_IMAGE_PLACEHOLDER_SRC =
  "https://dummyimage.com/480x480/e5e7eb/6b7280&text=No+Image";

/** Resolves the display URL for a store logo (hosted logo URL, proxied remote, or placeholder). */
export function resolveStoreImageSrc(item: StoreItem): string {
  const trimmedLogoImageUrl = item.logoImageUrl?.trim() ?? "";
  const trimmedImageUrl = item.imageUrl.trim();

  if (trimmedLogoImageUrl.length > 0) {
    if (
      trimmedLogoImageUrl.startsWith("http://") ||
      trimmedLogoImageUrl.startsWith("https://")
    ) {
      return trimmedLogoImageUrl;
    }
  }
  if (trimmedImageUrl.length > 0) {
    return `/api/image-proxy?url=${encodeURIComponent(trimmedImageUrl)}`;
  }
  return STORE_IMAGE_PLACEHOLDER_SRC;
}
