"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMapLocationDot, faTag, faXmark } from "@fortawesome/free-solid-svg-icons";
import type { StoreItem } from "@/components/StoreCard";
import {
  STORE_IMAGE_PLACEHOLDER_SRC,
  resolveStoreImageSrc,
} from "@/lib/resolveStoreImageSrc";

type StoreDetailModalProps = {
  item: StoreItem | null;
  onClose: () => void;
  onRefreshStoreProfile: (username: string) => Promise<{ ok: boolean }>;
};

export default function StoreDetailModal({
  item,
  onClose,
  onRefreshStoreProfile,
}: StoreDetailModalProps) {
  const isOpen = item !== null;

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen || !item) {
      return;
    }

    const normalizedTags = item.tags
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);
    const normalizedUsername = item.username.trim();
    if (normalizedTags.length > 0 || !normalizedUsername) {
      return;
    }

    void onRefreshStoreProfile(normalizedUsername);
  }, [isOpen, item, onRefreshStoreProfile]);

  if (!isOpen || !item) {
    return null;
  }

  const imageSrc = resolveStoreImageSrc(item);
  const instagramUsername = item.username.trim();
  const instagramProfileUrl = instagramUsername
    ? `https://instagram.com/${encodeURIComponent(instagramUsername)}`
    : "";
  const description = item.description.trim();
  const tags = item.tags.filter((tag) => tag.trim().length > 0);
  const addresses = item.addresses;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
      role="presentation"
    >
      <div
        className="store-detail-modal-backdrop absolute inset-0 bg-zinc-900/45"
        aria-hidden
        onMouseDown={onClose}
      />
      <div
        className="store-detail-modal-panel relative z-10 flex max-h-[min(90dvh,40rem)] w-full max-w-md flex-col overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-zinc-200"
        role="dialog"
        aria-modal="true"
        aria-labelledby="store-detail-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-full bg-white/95 text-zinc-500 shadow-sm ring-1 ring-zinc-200 transition hover:bg-zinc-50 hover:text-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pink-300"
          aria-label="Close store details"
        >
          <FontAwesomeIcon icon={faXmark} className="h-4 w-4" aria-hidden="true" />
        </button>

        <div className="store-detail-modal-scroll overflow-y-auto overscroll-contain px-5 pb-6 pt-5 sm:px-6 sm:pb-7 sm:pt-6">
          <div className="mx-auto aspect-square w-28 max-w-[40%] overflow-hidden rounded-2xl bg-zinc-100 ring-1 ring-zinc-200 sm:w-32">
            <img
              src={imageSrc}
              alt={`${item.fullName || item.username} profile`}
              className="h-full w-full object-cover"
              decoding="async"
              onError={(event) => {
                const failedSrc =
                  event.currentTarget.currentSrc || event.currentTarget.src;
                if (failedSrc !== STORE_IMAGE_PLACEHOLDER_SRC) {
                  event.currentTarget.src = STORE_IMAGE_PLACEHOLDER_SRC;
                }
              }}
            />
          </div>




          <h2 id="store-detail-title" className="sr-only">
            {item.fullName || item.username} store details
          </h2>

          {instagramUsername ? (
            <a
              href={instagramProfileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 block text-center text-lg font-semibold text-[#8134af] transition hover:text-[#dd2a7b] hover:underline"
            >
              @{instagramUsername}
            </a>
          ) : null}

          <section className="mt-5" aria-label="Description">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Description
            </h3>
            <p className="mt-1.5 text-sm leading-relaxed text-zinc-700">
              {description || (
                <span className="italic text-zinc-500">No description available.</span>
              )}
            </p>
          </section>

          <section className="mt-5" aria-label="Tags">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Tags
            </h3>
            {tags.length > 0 ? (
              <ul className="mt-2 flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <li
                    key={tag}
                    className="inline-flex items-center gap-1.5 rounded-full bg-zinc-100 px-2.5 py-1 text-sm text-zinc-600"
                  >
                    <FontAwesomeIcon
                      icon={faTag}
                      className="h-3 w-3 shrink-0 text-zinc-500"
                      aria-hidden="true"
                    />
                    <span>{tag}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1.5 text-sm italic text-zinc-500">No tags available.</p>
            )}
          </section>

          <section className="mt-5" aria-label="Location">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              Location
            </h3>
            {addresses.length > 0 ? (
              <ul className="mt-2 list-none space-y-2.5">
                {addresses.map((address, index) => (
                  <li
                    key={`${address}:${index}`}
                    className="flex items-start gap-2.5 text-sm leading-relaxed text-zinc-700"
                  >
                    <FontAwesomeIcon
                      icon={faMapLocationDot}
                      className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-500"
                      aria-hidden="true"
                    />
                    <span>{address}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1.5 text-sm italic text-zinc-500">
                No location available.
              </p>
            )}
          </section>
        </div>
      </div>
    </div>,
    document.body,
  );
}

