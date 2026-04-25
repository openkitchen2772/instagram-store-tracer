"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import StoreCard, { type StoreItem } from "@/components/StoreCard";
import StorebookHeader, { type ViewMode } from "@/components/StorebookHeader";
import TopBar from "@/components/TopBar";

type StorebookPageProps = {
  sessionUuid: string;
};

export default function StorebookPage({ sessionUuid }: StorebookPageProps) {
  const SCROLLBAR_EDGE_PADDING = 10;
  const STORE_API_URL = "http://localhost:8000/stores";
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [stores, setStores] = useState<StoreItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoadingStores, setIsLoadingStores] = useState(true);
  const [storesError, setStoresError] = useState<string | null>(null);
  const [isScrolling, setIsScrolling] = useState(false);
  const [thumbHeight, setThumbHeight] = useState(0);
  const [thumbOffset, setThumbOffset] = useState(0);
  const [showCustomScrollbar, setShowCustomScrollbar] = useState(false);
  const [headerHeight, setHeaderHeight] = useState(0);
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const headerRef = useRef<HTMLDivElement | null>(null);

  const filteredStores = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return stores;
    }

    return stores.filter((item) =>
      item.name.toLowerCase().includes(normalizedQuery),
    );
  }, [searchQuery, stores]);

  useEffect(() => {
    const controller = new AbortController();

    const fetchStores = async () => {
      setIsLoadingStores(true);
      setStoresError(null);

      try {
        const response = await fetch(STORE_API_URL, {
          method: "GET",
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch stores (HTTP ${response.status})`);
        }

        const payload = (await response.json()) as StoreItem[];
        setStores(payload);
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        const message =
          error instanceof Error ? error.message : "Failed to fetch stores";
        setStoresError(message);
      } finally {
        if (!controller.signal.aborted) {
          setIsLoadingStores(false);
        }
      }
    };

    fetchStores();

    return () => {
      controller.abort();
    };
  }, [STORE_API_URL]);

  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  const updateScrollbarMetrics = useCallback(() => {
    const element = scrollContainerRef.current;
    if (!element) return;

    const { clientHeight, scrollHeight, scrollTop } = element;
    const hasOverflow = scrollHeight > clientHeight + 1;
    setShowCustomScrollbar(hasOverflow);

    if (!hasOverflow) {
      setThumbHeight(0);
      setThumbOffset(0);
      return;
    }

    const trackTop = SCROLLBAR_EDGE_PADDING + headerHeight;
    const trackBottom = SCROLLBAR_EDGE_PADDING;
    const trackHeight = Math.max(clientHeight - trackTop - trackBottom, 1);
    const nextThumbHeight = Math.max((clientHeight / scrollHeight) * trackHeight, 40);
    const travel = Math.max(trackHeight - nextThumbHeight, 0);
    const maxScrollTop = Math.max(scrollHeight - clientHeight, 1);
    const nextThumbOffset = (scrollTop / maxScrollTop) * travel;

    setThumbHeight(nextThumbHeight);
    setThumbOffset(nextThumbOffset);
  }, [SCROLLBAR_EDGE_PADDING, headerHeight]);

  useEffect(() => {
    const updateHeaderHeight = () => {
      setHeaderHeight(headerRef.current?.offsetHeight ?? 0);
    };

    updateHeaderHeight();
    updateScrollbarMetrics();

    const element = scrollContainerRef.current;
    if (!element) return;

    const resizeObserver = new ResizeObserver(() => {
      updateHeaderHeight();
      updateScrollbarMetrics();
    });
    resizeObserver.observe(element);
    if (headerRef.current) {
      resizeObserver.observe(headerRef.current);
    }
    window.addEventListener("resize", updateScrollbarMetrics);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateScrollbarMetrics);
    };
  }, [filteredStores, viewMode, updateScrollbarMetrics]);

  const handleStorebookScroll = () => {
    updateScrollbarMetrics();
    setIsScrolling(true);

    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }

    scrollTimeoutRef.current = setTimeout(() => {
      setIsScrolling(false);
    }, 850);
  };

  return (
    <main className="h-dvh overflow-hidden bg-[radial-gradient(circle_at_15%_20%,rgba(245,133,41,0.22),transparent_38%),radial-gradient(circle_at_85%_12%,rgba(131,58,180,0.2),transparent_42%),radial-gradient(circle_at_50%_100%,rgba(225,48,108,0.18),transparent_45%),linear-gradient(180deg,#fff8fb_0%,#f7f7ff_100%)] px-4 py-5 text-zinc-900 sm:px-6 sm:py-6">
      <div className="mx-auto grid h-full w-full max-w-6xl grid-rows-[2fr_8fr] gap-4">
        <TopBar appName="IG Shop Tracer" sessionName={sessionUuid} />

        <section className="relative overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-black/5">
          <div
            ref={scrollContainerRef}
            className={`storebook-scroll h-full overflow-x-hidden overflow-y-auto overscroll-contain ${
              isScrolling ? "scrollbar-visible" : ""
            }`}
            onScroll={handleStorebookScroll}
          >
            <StorebookHeader
              viewMode={viewMode}
              searchQuery={searchQuery}
              onViewModeChange={setViewMode}
              onSearchChange={setSearchQuery}
              containerRef={headerRef}
            />

            <div className="px-4 pb-5 pt-2 sm:px-6 sm:pb-6">
              {isLoadingStores ? (
                <p className="rounded-2xl bg-zinc-50 px-4 py-6 text-sm text-zinc-600 ring-1 ring-zinc-200">
                  Loading stores...
                </p>
              ) : null}
              {storesError ? (
                <p className="mt-3 rounded-2xl bg-red-50 px-4 py-6 text-sm text-red-700 ring-1 ring-red-200">
                  Unable to load stores. {storesError}
                </p>
              ) : null}
              {viewMode === "grid" ? (
                <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
                  {filteredStores.map((item) => (
                    <StoreCard key={item.id} item={item} />
                  ))}
                </div>
              ) : (
                <div
                  className="rounded-2xl bg-zinc-50 p-5 text-zinc-700 ring-1 ring-zinc-200"
                  role="region"
                  aria-label="Map view"
                >
                  <h2 className="text-lg font-semibold text-zinc-900">Store Map View</h2>
                  <p className="pt-1 text-sm text-zinc-600">
                    Basic map placeholder with store coordinates.
                  </p>
                  <ul className="mt-4 grid gap-2 text-sm">
                    {filteredStores.map((item) => (
                      <li
                        key={item.id}
                        className="rounded-xl bg-white px-3 py-2 ring-1 ring-zinc-200"
                      >
                        {item.name}: ({item.latitude}, {item.longitude})
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {showCustomScrollbar ? (
            <div
              className={`pointer-events-none absolute bottom-[10px] right-[4px] top-[10px] w-[8px] rounded-full bg-zinc-200/30 transition-opacity duration-300 ${
                isScrolling ? "opacity-100" : "opacity-0"
              }`}
              style={{ top: `${headerHeight + SCROLLBAR_EDGE_PADDING}px` }}
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
          ) : null}
        </section>
      </div>
    </main>
  );
}
