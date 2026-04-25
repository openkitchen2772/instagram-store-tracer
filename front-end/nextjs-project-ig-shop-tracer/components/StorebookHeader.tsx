"use client";

import type { RefObject } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faGrip, faMapLocationDot } from "@fortawesome/free-solid-svg-icons";

export type ViewMode = "grid" | "map";

type StorebookHeaderProps = {
  viewMode: ViewMode;
  searchQuery: string;
  onViewModeChange: (nextView: ViewMode) => void;
  onSearchChange: (value: string) => void;
  containerRef?: RefObject<HTMLDivElement | null>;
};

export default function StorebookHeader({
  viewMode,
  searchQuery,
  onViewModeChange,
  onSearchChange,
  containerRef,
}: StorebookHeaderProps) {
  const baseButtonClass =
    "flex h-10 w-10 items-center justify-center rounded-full border text-base transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300";

  return (
    <div
      ref={containerRef}
      className="sticky top-0 z-20 flex flex-col gap-3 bg-white/90 px-4 py-3 backdrop-blur-sm sm:flex-row sm:items-center sm:justify-between sm:px-6"
    >
      <div className="flex items-center gap-2">
        <button
          type="button"
          className={`${baseButtonClass} ${
            viewMode === "grid"
              ? "border-zinc-900 bg-zinc-900 text-white"
              : "border-zinc-300 bg-white text-zinc-700 hover:border-zinc-400"
          }`}
          onClick={() => onViewModeChange("grid")}
          aria-label="Switch to grid view"
        >
          <FontAwesomeIcon icon={faGrip} aria-hidden="true" />
        </button>
        <button
          type="button"
          className={`${baseButtonClass} ${
            viewMode === "map"
              ? "border-zinc-900 bg-zinc-900 text-white"
              : "border-zinc-300 bg-white text-zinc-700 hover:border-zinc-400"
          }`}
          onClick={() => onViewModeChange("map")}
          aria-label="Switch to map view"
        >
          <FontAwesomeIcon icon={faMapLocationDot} aria-hidden="true" />
        </button>
      </div>

      <input
        type="search"
        value={searchQuery}
        onChange={(event) => onSearchChange(event.target.value)}
        className="h-11 w-full rounded-full border border-zinc-300 bg-white px-4 text-sm text-zinc-800 outline-none transition focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200 sm:max-w-xs"
        placeholder="Search store"
        aria-label="Search stores"
      />
    </div>
  );
}
