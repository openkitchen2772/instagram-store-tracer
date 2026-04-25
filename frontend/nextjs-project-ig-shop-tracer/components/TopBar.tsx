"use client";

type TopBarProps = {
  appName: string;
  sessionName: string;
};

export default function TopBar({ appName, sessionName }: TopBarProps) {
  return (
    <header className="flex h-full items-center justify-between gap-4 rounded-2xl bg-white px-5 shadow-sm ring-1 ring-black/5 sm:px-7">
      <div className="min-w-0">
        <h1 className="app-title text-2xl leading-tight sm:text-3xl">
          {appName}
        </h1>
        <p className="mt-1 max-w-xl text-xs leading-relaxed text-zinc-600 sm:text-sm">
          Bookmark, search, view, and track favorite Instagram stores in one place.
        </p>
      </div>
      <div className="max-w-[58%] truncate rounded-full border border-zinc-200 bg-zinc-50 px-4 py-2 font-mono text-xs text-zinc-600 sm:max-w-[50%]">
        {sessionName}
      </div>
    </header>
  );
}
