"use client";

type TopBarProps = {
  appName: string;
  sessionName: string;
};

export default function TopBar({ appName, sessionName }: TopBarProps) {
  return (
    <header className="flex min-w-0 shrink-0 flex-col gap-3 rounded-2xl bg-white px-4 py-3 shadow-sm ring-1 ring-black/5 sm:flex-row sm:items-center sm:justify-between sm:gap-5 sm:px-7 sm:py-5 md:gap-6 md:px-8 md:py-6 lg:py-7">
      <div className="min-w-0">
        <h1 className="app-title text-xl leading-tight sm:text-3xl md:text-[2rem]">
          {appName}
        </h1>
        <p className="mt-1 max-w-xl text-xs leading-relaxed text-zinc-600 sm:mt-1.5 sm:text-sm md:mt-2">
          Bookmark, search, view, and track favorite Instagram stores in one place.
        </p>
      </div>
      <div className="w-full min-w-0 truncate rounded-full border border-zinc-200 bg-zinc-50 px-3 py-2 font-mono text-[0.65rem] text-zinc-600 sm:w-auto sm:max-w-none sm:shrink-0 sm:truncate-none sm:whitespace-nowrap sm:px-3 sm:py-1.5 sm:text-xs">
        {sessionName}
      </div>
    </header>
  );
}
