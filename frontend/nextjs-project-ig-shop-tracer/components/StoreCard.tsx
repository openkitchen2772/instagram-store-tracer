export type StoreItem = {
  id: string;
  name: string;
  imageUrl: string;
  localLogoPath?: string;
  latitude: number;
  longitude: number;
};

type StoreCardProps = {
  item: StoreItem;
};

export default function StoreCard({ item }: StoreCardProps) {
  const backendOrigin = "http://localhost:8000";
  const trimmedLocalLogoPath = item.localLogoPath?.trim() ?? "";
  const trimmedImageUrl = item.imageUrl.trim();
  const placeholderSrc = "https://dummyimage.com/480x480/e5e7eb/6b7280&text=No+Image";
  const hasLocalLogoPath = trimmedLocalLogoPath.length > 0;
  const localLogoAbsoluteUrl =
    trimmedLocalLogoPath.startsWith("/")
      ? `${backendOrigin}${trimmedLocalLogoPath}`
      : `${backendOrigin}/${trimmedLocalLogoPath}`;
  const resolvedImageSrc = hasLocalLogoPath
    ? localLogoAbsoluteUrl
    : trimmedImageUrl.length > 0
      ? `/api/image-proxy?url=${encodeURIComponent(trimmedImageUrl)}`
      : placeholderSrc;

  return (
    <article className="rounded-2xl border border-zinc-200 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="relative aspect-square w-full overflow-hidden rounded-xl bg-zinc-100">
        <img
          src={resolvedImageSrc}
          alt={item.name}
          className="h-full w-full object-cover"
          loading="lazy"
          decoding="async"
          onError={(event) => {
            const failedSrc = event.currentTarget.currentSrc || event.currentTarget.src;
            if (failedSrc !== placeholderSrc) {
              event.currentTarget.src = placeholderSrc;
            }
          }}
        />
      </div>
      <p className="pt-3 text-center text-sm font-medium text-zinc-800">{item.name}</p>
    </article>
  );
}
