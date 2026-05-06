"use client";

/**
 * FloatingStoreSubmitter
 *
 * Floating action button (FAB) that expands into an input + submit control for
 * adding a new Instagram store. The component owns all of its local UI state
 * (open/closed, input value, in-flight submission) so the parent only has to
 * provide the async submit handler.
 *
 * Outside-click handling: clicks inside the floating container (including the
 * `children` slot rendered above the form) do NOT close the input. This mirrors
 * the original UX where toast messages stacked above the FAB are considered
 * "inside" the control.
 *
 * Escape key also closes the input, for keyboard users.
 */

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPaperPlane,
  faPlus,
  faSpinner,
} from "@fortawesome/free-solid-svg-icons";

type FloatingStoreSubmitterProps = {
  /**
   * Called when the user submits a non-empty (trimmed) store name. Resolve
   * with `true` on success — the component then clears the input and closes.
   * Resolve with `false` to keep the input open so the user can retry.
   */
  onSubmit: (storeName: string) => Promise<boolean>;
  /**
   * Optional slot rendered above the FAB/form (e.g. toast messages). Clicks
   * inside this slot are treated as "inside" for outside-click detection.
   */
  children?: ReactNode;
};

export default function FloatingStoreSubmitter({
  onSubmit,
  children,
}: FloatingStoreSubmitterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDownOutside = (event: MouseEvent | TouchEvent) => {
      const targetNode = event.target as Node | null;
      if (!targetNode) return;
      if (containerRef.current?.contains(targetNode)) return;

      if (isSubmitting) return;

      setIsOpen(false);
      setValue("");
    };

    document.addEventListener("mousedown", handlePointerDownOutside);
    document.addEventListener("touchstart", handlePointerDownOutside);

    return () => {
      document.removeEventListener("mousedown", handlePointerDownOutside);
      document.removeEventListener("touchstart", handlePointerDownOutside);
    };
  }, [isOpen, isSubmitting]);

  const handleOpen = () => setIsOpen(true);
  const handleClose = () => {
    if (isSubmitting) return;
    setIsOpen(false);
    setValue("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const ok = await onSubmit(trimmed);
      if (ok) {
        setValue("");
        setIsOpen(false);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      ref={containerRef}
      className="pointer-events-none fixed bottom-6 right-5 z-40 flex flex-col items-end sm:bottom-8 sm:right-10"
    >
      {children}

      {isSubmitting ? (
        <p className="pointer-events-none mb-2 rounded-full bg-white/95 px-3 py-1 text-xs font-medium text-zinc-700 shadow-sm ring-1 ring-zinc-200">
          Processing store submission...
        </p>
      ) : null}

      <form
        className={`pointer-events-auto flex h-14 origin-right items-center overflow-hidden rounded-full bg-white shadow-[0_10px_30px_rgba(225,48,108,0.28)] ring-1 ring-zinc-300 transition-all duration-300 ease-out ${
          isOpen ? "w-[min(85vw,22rem)] opacity-100" : "w-14 opacity-100"
        }`}
        onSubmit={handleSubmit}
        aria-busy={isSubmitting}
      >
        {isOpen ? (
          <>
            <input
              ref={inputRef}
              type="text"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape") handleClose();
              }}
              className="h-full w-full bg-white pl-5 pr-2 text-sm text-zinc-800 outline-none"
              placeholder={
                isSubmitting
                  ? "Processing submission..."
                  : "Submit Instagram store name"
              }
              aria-label="Instagram store name"
              disabled={isSubmitting}
            />
            <button
              type="submit"
              disabled={isSubmitting}
              className="mr-2 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(135deg,#f58529_0%,#dd2a7b_50%,#8134af_100%)] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pink-300"
              aria-label={isSubmitting ? "Submitting store name" : "Submit store name"}
            >
              <FontAwesomeIcon
                icon={isSubmitting ? faSpinner : faPaperPlane}
                className={isSubmitting ? "animate-spin" : undefined}
                aria-hidden="true"
              />
            </button>
          </>
        ) : (
          <button
            type="button"
            className="relative h-full w-full rounded-full bg-[linear-gradient(145deg,#f58529_0%,#dd2a7b_55%,#515bd4_100%)] text-white transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pink-300"
            onClick={handleOpen}
            aria-label="Add Instagram store"
          >
            <span className="absolute inset-0 flex items-center justify-center text-[1.7rem] leading-none">
              <FontAwesomeIcon icon={faPlus} aria-hidden="true" />
            </span>
          </button>
        )}
      </form>
    </div>
  );
}
