import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMinus, faTag } from "@fortawesome/free-solid-svg-icons";
import { useMemo } from "react";
import {
  STORE_IMAGE_PLACEHOLDER_SRC,
  resolveStoreImageSrc,
} from "@/lib/resolveStoreImageSrc";

export type StoreLocation = {
  latitude: number;
  longitude: number;
};

export type StoreItem = {
  id: string;
  objectId: string;
  username: string;
  fullName: string;
  imageUrl: string;
  localLogoPath?: string;
  latitude: number;
  longitude: number;
  description: string;
  tags: string[];
  storeLocations: StoreLocation[];
  addresses: string[];
};

type StoreCardProps = {
  item: StoreItem;
  onSelect?: (item: StoreItem) => void;
  onDelete?: (item: StoreItem) => void;
  isDeleting?: boolean;
};

export default function StoreCard({
  item,
  onSelect,
  onDelete,
  isDeleting = false,
}: StoreCardProps) {
  const resolvedImageSrc = resolveStoreImageSrc(item);
  const isInteractive = Boolean(onSelect);
  const randomTags = useMemo(() => {
    const validTags = item.tags
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);

    if (validTags.length <= 3) {
      return validTags;
    }

    const shuffledTags = [...validTags];
    for (let index = shuffledTags.length - 1; index > 0; index -= 1) {
      const randomIndex = Math.floor(Math.random() * (index + 1));
      [shuffledTags[index], shuffledTags[randomIndex]] = [
        shuffledTags[randomIndex],
        shuffledTags[index],
      ];
    }

    return shuffledTags.slice(0, 3);
  }, [item.tags]);
  return (
    <article
      className={`group relative min-w-0 rounded-2xl border border-zinc-200 bg-white p-2.5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md sm:p-3 ${
        isInteractive ? "cursor-pointer" : ""
      }`}
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      onClick={isInteractive ? () => onSelect?.(item) : undefined}
      onKeyDown={
        isInteractive
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect?.(item);
              }
            }
          : undefined
      }
    >
      <div className="relative aspect-square w-full overflow-hidden rounded-xl bg-zinc-100">
        {onDelete ? (
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onDelete(item);
            }}
            disabled={isDeleting}
            className="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-white/90 text-zinc-400 shadow-sm ring-1 ring-zinc-200 transition hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-60"
            aria-label={`Remove ${item.fullName || item.username}`}
          >
            <FontAwesomeIcon icon={faMinus} className="h-3 w-3" aria-hidden="true" />
          </button>
        ) : null}
        <img
          src={resolvedImageSrc}
          alt={item.fullName || item.username}
          className="h-full w-full object-cover"
          loading="lazy"
          decoding="async"
          onError={(event) => {
            const failedSrc = event.currentTarget.currentSrc || event.currentTarget.src;
            if (failedSrc !== STORE_IMAGE_PLACEHOLDER_SRC) {
              event.currentTarget.src = STORE_IMAGE_PLACEHOLDER_SRC;
            }
          }}
        />
      </div>
      <p className="line-clamp-2 break-words pt-2 text-center text-xs font-medium text-zinc-800 sm:pt-3 sm:text-sm">
        {item.fullName || item.username}
      </p>
      {randomTags.length > 0 ? (
        <ul className="mt-1.5 flex flex-wrap justify-center gap-1 sm:mt-2 sm:gap-1.5">
          {randomTags.map((tag) => (
            <li
              key={tag}
              className="inline-flex max-w-full items-center gap-1 rounded-full bg-zinc-100 px-1.5 py-0.5 text-[0.65rem] text-zinc-600 sm:gap-1.5 sm:px-2 sm:text-xs"
            >
              <FontAwesomeIcon
                icon={faTag}
                className="h-2.5 w-2.5 shrink-0 text-zinc-500 sm:h-3 sm:w-3"
                aria-hidden="true"
              />
              <span className="truncate">{tag}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}
