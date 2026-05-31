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

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { StoreItem } from "@/components/StoreCard";
import { useBookmarkSessionId } from "@/hooks/useBookmarkSessionId";
import CustomScrollbar from "@/components/common/CustomScrollbar";
import StorebookHeader, { type ViewMode } from "@/components/StorebookHeader";
import TopBar from "@/components/TopBar";
import FloatingStoreSubmitter from "@/components/storebook/FloatingStoreSubmitter";
import StoreDetailModal from "@/components/storebook/StoreDetailModal";
import StoreListView from "@/components/storebook/StoreListView";
import SubmitMessageStack from "@/components/storebook/SubmitMessageStack";
import { useClientSettings } from "@/hooks/useClientSettings";
import { useCustomScrollbar } from "@/hooks/useCustomScrollbar";
import { useStores } from "@/hooks/useStores";
import { useSubmitMessages } from "@/hooks/useSubmitMessages";

// Padding (px) between the storebook section edges and the custom scrollbar
// track. The same value is reused for both the top and bottom so the overlay
// is visually centered within the rounded container.
const SCROLLBAR_EDGE_PADDING = 10;

type StorebookPageProps = {
  /** When set (e.g. `?uuid=...`), loads that bookmark session without changing localStorage. */
  bookmarksUuidFromUrl?: string;
};

export default function StorebookPage({
  bookmarksUuidFromUrl,
}: StorebookPageProps) {
  const sessionUuid = useBookmarkSessionId();
  const bookmarksUuid = bookmarksUuidFromUrl ?? sessionUuid;
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [isDeleteMode, setIsDeleteMode] = useState(false);
  const [selectedStore, setSelectedStore] = useState<StoreItem | null>(null);

  // The page owns the refs for both the scroll container and the sticky
  // StorebookHeader; they are handed to `useCustomScrollbar` as inputs so the
  // hook stays ignorant of page-specific layout concerns.
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const headerRef = useRef<HTMLDivElement | null>(null);

  const { stores, isLoading, error, submitStore, deleteStore, getStoreProfile } =
    useStores(bookmarksUuid);
  const {
    googleMapsApiKey,
    isLoading: isSettingsLoading,
    error: settingsError,
  } = useClientSettings();
  const [deletingStoreObjectId, setDeletingStoreObjectId] = useState<
    string | null
  >(null);
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
    return stores.filter((item) => {
      const matchesFullName = item.fullName.toLowerCase().includes(normalizedQuery);
      const matchesUsername = item.username.toLowerCase().includes(normalizedQuery);
      const matchesTags = item.tags.some((tag) =>
        tag.toLowerCase().includes(normalizedQuery),
      );
      return matchesFullName || matchesUsername || matchesTags;
    });
  }, [searchQuery, stores]);

  const handleSubmitStore = async (storeName: string): Promise<boolean> => {
    const result = await submitStore(storeName);
    showMessage(result.ok ? "Store submitted" : "Unable to submit store");
    return result.ok;
  };

  const handleDeleteStore = useCallback(
    async (item: StoreItem) => {
      const storeObjectId = item.objectId.trim();
      if (!storeObjectId) {
        showMessage("Unable to remove store");
        return;
      }

      setDeletingStoreObjectId(storeObjectId);
      const result = await deleteStore(storeObjectId);
      setDeletingStoreObjectId(null);
      showMessage(result.ok ? "Store removed" : "Unable to remove store");
    },
    [deleteStore, showMessage],
  );

  useEffect(() => {
    if (!selectedStore) {
      return;
    }

    const matchedStore = stores.find((store) => {
      if (selectedStore.objectId.trim() && store.objectId.trim()) {
        return store.objectId === selectedStore.objectId;
      }
      return store.id === selectedStore.id;
    });

    if (!matchedStore) {
      setSelectedStore(null);
      return;
    }

    if (matchedStore !== selectedStore) {
      setSelectedStore(matchedStore);
    }
  }, [selectedStore, stores]);

  return (
    <main className="h-dvh overflow-hidden bg-[radial-gradient(circle_at_15%_20%,rgba(245,133,41,0.22),transparent_38%),radial-gradient(circle_at_85%_12%,rgba(131,58,180,0.2),transparent_42%),radial-gradient(circle_at_50%_100%,rgba(225,48,108,0.18),transparent_45%),linear-gradient(180deg,#fff8fb_0%,#f7f7ff_100%)] px-3 py-4 text-zinc-900 sm:px-6 sm:py-6">
      <div className="mx-auto grid h-full w-full min-w-0 max-w-6xl grid-rows-[auto_1fr] gap-3 sm:gap-4">
        <TopBar
          appName="Instagram Shop Tracer"
          sessionName={bookmarksUuid ?? "…"}
        />

        <section className="relative min-h-0 overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-black/5">
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
              isDeleteMode={isDeleteMode}
              onViewModeChange={setViewMode}
              onSearchChange={setSearchQuery}
              onDeleteModeToggle={() => setIsDeleteMode((current) => !current)}
              containerRef={headerRef}
            />
            <StoreListView
              viewMode={viewMode}
              stores={filteredStores}
              isLoading={isLoading}
              error={error}
              googleMapsApiKey={googleMapsApiKey}
              isSettingsLoading={isSettingsLoading}
              settingsError={settingsError}
              isFavoriteListEmpty={
                bookmarksUuid !== null &&
                !isLoading &&
                !error &&
                stores.length === 0
              }
              hasBookmarks={stores.length > 0}
              isDeleteMode={isDeleteMode}
              onStoreSelect={setSelectedStore}
              onDeleteStore={handleDeleteStore}
              deletingStoreObjectId={deletingStoreObjectId}
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

      <StoreDetailModal
        item={selectedStore}
        onClose={() => setSelectedStore(null)}
        onRefreshStoreProfile={getStoreProfile}
      />
    </main>
  );
}
