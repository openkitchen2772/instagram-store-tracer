"use client";

/**
 * StorebookPage
 *
 * Top-level orchestration component for the storebook route. It owns only
 * page-level concerns:
 *
 *   - Page chrome (background gradient, `TopBar`, rounded content section).
 *   - Local UI state that spans children (`viewMode`, `searchQuery`).
 *   - Wiring the reusable hooks (`useStores`, `useCustomScrollbar`,
 *     `useSubmitMessages`) to the dedicated child components
 *     (`StoreListView`, `CustomScrollbar`, `FloatingStoreSubmitter`,
 *     `SubmitMessageStack`).
 *
 * Feature-specific logic (data fetching, floating FAB state, toast queue,
 * scrollbar metrics) lives in the respective hooks/components so this file
 * stays focused on composition.
 */

import { useMemo, useRef, useState } from "react";
import CustomScrollbar from "@/components/common/CustomScrollbar";
import StorebookHeader, { type ViewMode } from "@/components/StorebookHeader";
import TopBar from "@/components/TopBar";
import FloatingStoreSubmitter from "@/components/storebook/FloatingStoreSubmitter";
import StoreListView from "@/components/storebook/StoreListView";
import SubmitMessageStack from "@/components/storebook/SubmitMessageStack";
import { useCustomScrollbar } from "@/hooks/useCustomScrollbar";
import { useStores } from "@/hooks/useStores";
import { useSubmitMessages } from "@/hooks/useSubmitMessages";

type StorebookPageProps = {
  sessionUuid: string;
};

// Padding (px) between the storebook section edges and the custom scrollbar
// track. The same value is reused for both the top and bottom so the overlay
// is visually centered within the rounded container.
const SCROLLBAR_EDGE_PADDING = 10;

export default function StorebookPage({ sessionUuid }: StorebookPageProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [searchQuery, setSearchQuery] = useState("");

  // The page owns the refs for both the scroll container and the sticky
  // StorebookHeader; they are handed to `useCustomScrollbar` as inputs so the
  // hook stays ignorant of page-specific layout concerns.
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const headerRef = useRef<HTMLDivElement | null>(null);

  const { stores, isLoading, error, submitStore } = useStores();
  const scrollbar = useCustomScrollbar({
    containerRef: scrollContainerRef,
    topInsetRef: headerRef,
    edgePadding: SCROLLBAR_EDGE_PADDING,
  });
  const { messages, showMessage } = useSubmitMessages();

  const filteredStores = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return stores;
    }
    return stores.filter((item) =>
      item.name.toLowerCase().includes(normalizedQuery),
    );
  }, [searchQuery, stores]);

  const handleSubmitStore = async (storeName: string): Promise<boolean> => {
    const result = await submitStore(storeName);
    showMessage(result.ok ? "Store submitted" : "Unable to submit store");
    return result.ok;
  };

  return (
    <main className="h-dvh overflow-hidden bg-[radial-gradient(circle_at_15%_20%,rgba(245,133,41,0.22),transparent_38%),radial-gradient(circle_at_85%_12%,rgba(131,58,180,0.2),transparent_42%),radial-gradient(circle_at_50%_100%,rgba(225,48,108,0.18),transparent_45%),linear-gradient(180deg,#fff8fb_0%,#f7f7ff_100%)] px-4 py-5 text-zinc-900 sm:px-6 sm:py-6">
      <div className="mx-auto grid h-full w-full max-w-6xl grid-rows-[2fr_8fr] gap-4">
        <TopBar appName="IG Shop Tracer" sessionName={sessionUuid} />

        <section className="relative overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-black/5">
          <div
            ref={scrollContainerRef}
            className={`storebook-scroll h-full overflow-x-hidden overflow-y-auto overscroll-contain ${
              scrollbar.isScrolling ? "scrollbar-visible" : ""
            }`}
            onScroll={scrollbar.onScroll}
          >
            <StorebookHeader
              viewMode={viewMode}
              searchQuery={searchQuery}
              onViewModeChange={setViewMode}
              onSearchChange={setSearchQuery}
              containerRef={headerRef}
            />
            <StoreListView
              viewMode={viewMode}
              stores={filteredStores}
              isLoading={isLoading}
              error={error}
            />
          </div>

          <CustomScrollbar
            show={scrollbar.showScrollbar}
            isActive={scrollbar.isScrolling}
            thumbHeight={scrollbar.thumbHeight}
            thumbOffset={scrollbar.thumbOffset}
            topOffset={scrollbar.topInset + SCROLLBAR_EDGE_PADDING}
            bottomOffset={SCROLLBAR_EDGE_PADDING}
          />
        </section>
      </div>

      <FloatingStoreSubmitter onSubmit={handleSubmitStore}>
        <SubmitMessageStack messages={messages} />
      </FloatingStoreSubmitter>
    </main>
  );
}
