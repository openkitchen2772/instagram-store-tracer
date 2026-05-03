"use client";

/**
 * useCustomScrollbar
 *
 * Computes the metrics required to render a custom scrollbar overlay for any
 * vertically-scrolling container. The hook is intentionally generic: it knows
 * nothing about sticky headers, toolbars, or page layout. Callers that want
 * the track to sit below a sticky element pass its ref via `topInsetRef` and
 * the hook reserves that element's offset height at the top of the track, so
 * the scrollbar thumb is never rendered underneath it.
 *
 * The caller creates and owns both refs (the scroll container and the optional
 * top-inset element) and passes them in. The hook itself returns only plain
 * state values, which keeps the API compatible with React's render-time rules
 * about ref access.
 *
 * Collaborators:
 *   - `components/common/CustomScrollbar.tsx` consumes the returned metrics.
 *   - Callers attach their own `containerRef` to the scroll container and
 *     wire `onScroll` returned from this hook to that container's handler.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { RefObject } from "react";

export type UseCustomScrollbarOptions = {
  /** Ref to the scrollable container element. Owned by the caller. */
  containerRef: RefObject<HTMLElement | null>;
  /**
   * Optional ref to a "top inset" element whose measured height should be
   * excluded from the track region (for example a sticky header, toolbar, or
   * banner belonging to the caller). When omitted `topInset` stays at 0 and
   * the track simply uses `edgePadding` at the top.
   */
  topInsetRef?: RefObject<HTMLElement | null>;
  /** Padding (px) reserved at the bottom edge of the track. Default: 10 px. */
  edgePadding?: number;
};

export type UseCustomScrollbarResult = {
  /** Attach to the scrollable container's `onScroll` handler. */
  onScroll: () => void;
  /** True briefly after any scroll activity (850 ms idle debounce). */
  isScrolling: boolean;
  /** True when the content overflows and a scrollbar should be shown. */
  showScrollbar: boolean;
  /** Height (px) of the scrollbar thumb. */
  thumbHeight: number;
  /** Vertical offset (px) of the thumb from the top of the track. */
  thumbOffset: number;
  /** Measured top inset (px). Always 0 when no `topInsetRef` was provided. */
  topInset: number;
  /** Imperatively recompute metrics (rarely needed; observers handle most cases). */
  recompute: () => void;
};

// Minimum thumb height so the handle is always grabbable even with tall content.
const MIN_THUMB_HEIGHT_PX = 40;
// How long the `isScrolling` flag stays true after scroll activity stops.
const SCROLL_IDLE_TIMEOUT_MS = 850;
const DEFAULT_EDGE_PADDING = 10;

export function useCustomScrollbar(
  options: UseCustomScrollbarOptions,
): UseCustomScrollbarResult {
  const {
    containerRef,
    topInsetRef,
    edgePadding = DEFAULT_EDGE_PADDING,
  } = options;

  const scrollIdleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [isScrolling, setIsScrolling] = useState(false);
  const [showScrollbar, setShowScrollbar] = useState(false);
  const [thumbHeight, setThumbHeight] = useState(0);
  const [thumbOffset, setThumbOffset] = useState(0);
  const [topInset, setTopInset] = useState(0);

  const recompute = useCallback(() => {
    const container = containerRef.current as HTMLElement | null;
    if (!container) return;

    const nextTopInset = topInsetRef?.current?.offsetHeight ?? 0;
    setTopInset(nextTopInset);

    const { clientHeight, scrollHeight, scrollTop } = container;
    // `+ 1` guards against sub-pixel rounding that can falsely report overflow.
    const hasOverflow = scrollHeight > clientHeight + 1;
    setShowScrollbar(hasOverflow);

    if (!hasOverflow) {
      setThumbHeight(0);
      setThumbOffset(0);
      return;
    }

    const trackTop = edgePadding + nextTopInset;
    const trackBottom = edgePadding;
    const trackHeight = Math.max(clientHeight - trackTop - trackBottom, 1);
    const nextThumbHeight = Math.max(
      (clientHeight / scrollHeight) * trackHeight,
      MIN_THUMB_HEIGHT_PX,
    );
    const travel = Math.max(trackHeight - nextThumbHeight, 0);
    const maxScrollTop = Math.max(scrollHeight - clientHeight, 1);

    setThumbHeight(nextThumbHeight);
    setThumbOffset((scrollTop / maxScrollTop) * travel);
  }, [containerRef, edgePadding, topInsetRef]);

  const onScroll = useCallback(() => {
    recompute();
    setIsScrolling(true);

    if (scrollIdleTimerRef.current) {
      clearTimeout(scrollIdleTimerRef.current);
    }
    scrollIdleTimerRef.current = setTimeout(() => {
      setIsScrolling(false);
    }, SCROLL_IDLE_TIMEOUT_MS);
  }, [recompute]);

  // Observe everything that can change scrollbar geometry: container size,
  // top-inset element size (if provided), content structure changes, and
  // window resizes. The hook should "just work" without callers having to
  // trigger recomputes manually when their content updates.
  useEffect(() => {
    const container = containerRef.current as HTMLElement | null;
    if (!container) return;

    recompute();

    const resizeObserver = new ResizeObserver(() => recompute());
    resizeObserver.observe(container);

    const topInsetEl = topInsetRef?.current;
    if (topInsetEl) {
      resizeObserver.observe(topInsetEl);
    }

    // ResizeObserver does not fire when a container's `scrollHeight` changes
    // due to added/removed children (only when its own box size changes).
    // A MutationObserver on the subtree covers the content-changed case.
    const mutationObserver = new MutationObserver(() => recompute());
    mutationObserver.observe(container, {
      childList: true,
      subtree: true,
    });

    window.addEventListener("resize", recompute);

    return () => {
      resizeObserver.disconnect();
      mutationObserver.disconnect();
      window.removeEventListener("resize", recompute);
    };
  }, [containerRef, recompute, topInsetRef]);

  useEffect(() => {
    return () => {
      if (scrollIdleTimerRef.current) {
        clearTimeout(scrollIdleTimerRef.current);
      }
    };
  }, []);

  return {
    onScroll,
    isScrolling,
    showScrollbar,
    thumbHeight,
    thumbOffset,
    topInset,
    recompute,
  };
}
