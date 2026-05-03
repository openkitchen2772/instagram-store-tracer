"use client";

/**
 * CustomScrollbar
 *
 * Presentational overlay that renders a minimal custom scrollbar (track + thumb)
 * on top of any scroll container. It is entirely unaware of headers, toolbars,
 * or the page layout; callers supply the geometry via props:
 *
 *   - `topOffset` is the total pixels reserved at the top of the container
 *     (include any caller-owned sticky-element height here).
 *   - `bottomOffset` is the pixels reserved at the bottom. Defaults to 10 px.
 *
 * The component expects to be a sibling of the scroll container inside a
 * positioned ancestor (e.g. `<section class="relative">`) so the absolute
 * positioning lines up with the container.
 *
 * Collaborators: `hooks/useCustomScrollbar.ts` computes `thumbHeight`,
 * `thumbOffset`, `show`, and `isActive`.
 */

type CustomScrollbarProps = {
  /** Whether the scrollbar should render at all (usually true only when content overflows). */
  show: boolean;
  /** When true, the track fades in to full opacity (normally during active scrolling). */
  isActive: boolean;
  /** Height of the thumb in pixels. */
  thumbHeight: number;
  /** Vertical translation of the thumb from the top of the track. */
  thumbOffset: number;
  /** Pixels reserved at the top of the scroll container. Include any sticky-inset height here. */
  topOffset: number;
  /** Pixels reserved at the bottom of the scroll container. Default: 10 px. */
  bottomOffset?: number;
};

const DEFAULT_BOTTOM_OFFSET_PX = 10;

export default function CustomScrollbar({
  show,
  isActive,
  thumbHeight,
  thumbOffset,
  topOffset,
  bottomOffset = DEFAULT_BOTTOM_OFFSET_PX,
}: CustomScrollbarProps) {
  if (!show) return null;

  return (
    <div
      className={`pointer-events-none absolute right-[4px] w-[8px] rounded-full bg-zinc-200/30 transition-opacity duration-300 ${
        isActive ? "opacity-100" : "opacity-0"
      }`}
      style={{
        top: `${topOffset}px`,
        bottom: `${bottomOffset}px`,
      }}
      aria-hidden="true"
    >
      <div
        className="absolute left-0 w-full rounded-full bg-zinc-500/60 transition-[transform,opacity] duration-300"
        style={{
          height: `${thumbHeight}px`,
          transform: `translateY(${thumbOffset}px)`,
        }}
      />
    </div>
  );
}
