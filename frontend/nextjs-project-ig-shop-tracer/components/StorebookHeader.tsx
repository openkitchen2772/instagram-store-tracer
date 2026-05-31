"use client";

import type { RefObject } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faGrip,
  faMapLocationDot,
  faTrash,
} from "@fortawesome/free-solid-svg-icons";

export type ViewMode = "grid" | "map";

type StorebookHeaderProps = {
  viewMode: ViewMode;
  searchQuery: string;
  isDeleteMode: boolean;
  onViewModeChange: (nextView: ViewMode) => void;
  onSearchChange: (value: string) => void;
  onDeleteModeToggle: () => void;
  containerRef?: RefObject<HTMLDivElement | null>;
};

export default function StorebookHeader({
  viewMode,
  searchQuery,
  isDeleteMode,
  onViewModeChange,
  onSearchChange,
  onDeleteModeToggle,
  containerRef,
}: StorebookHeaderProps) {
  const baseButtonClass =
    "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-base transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-300 sm:h-10 sm:w-10";

  return (
    <div
      ref={containerRef}
      className="sticky top-0 z-20 flex min-w-0 flex-col gap-2.5 bg-white/90 px-3 py-2.5 backdrop-blur-sm sm:flex-row sm:items-center sm:justify-between sm:gap-3 sm:px-6 sm:py-3"
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

      <div className="flex w-full items-center gap-2 sm:max-w-sm">
        <input
          type="search"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
          className="h-10 min-w-0 flex-1 rounded-full border border-zinc-300 bg-white px-3 text-sm text-zinc-800 outline-none transition focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200 sm:h-11 sm:px-4"
          placeholder="Search store"
          aria-label="Search stores"
        />
        <button
          type="button"
          className={`${baseButtonClass} shrink-0 ${
            isDeleteMode
              ? "border-red-300 bg-red-50 text-red-600 hover:border-red-400"
              : "border-zinc-300 bg-white text-zinc-400 hover:border-zinc-400 hover:text-zinc-600"
          }`}
          onClick={onDeleteModeToggle}
          aria-label={isDeleteMode ? "Exit delete mode" : "Enter delete mode"}
          aria-pressed={isDeleteMode}
        >
          <FontAwesomeIcon icon={faTrash} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
