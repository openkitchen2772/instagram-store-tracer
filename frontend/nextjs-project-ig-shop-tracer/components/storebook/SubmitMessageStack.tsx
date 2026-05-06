"use client";

/**
 * SubmitMessageStack
 *
 * Purely presentational stack of toast-style messages. Visibility and cleanup
 * are driven by the `messages` array, which is typically produced by
 * `hooks/useSubmitMessages.ts`. Messages fade via the `isVisible` flag so the
 * DOM element stays mounted briefly after becoming invisible to allow the
 * CSS transition to run.
 */

import type { SubmitMessage } from "@/hooks/useSubmitMessages";

type SubmitMessageStackProps = {
  messages: SubmitMessage[];
};

export default function SubmitMessageStack({
  messages,
}: SubmitMessageStackProps) {
  return (
    <div className="mb-4 flex flex-col items-end gap-2">
      {messages.map((message) => (
        <p
          key={message.id}
          className={`w-max rounded-2xl bg-white/95 px-5 py-3 text-center text-sm font-semibold text-zinc-800 shadow-[0_10px_25px_rgba(131,58,180,0.14)] ring-1 ring-white transition-all duration-300 sm:text-base ${
            message.isVisible
              ? "translate-y-0 opacity-100"
              : "pointer-events-none translate-y-1 opacity-0"
          }`}
          role="status"
          aria-live="polite"
        >
          {message.text}
        </p>
      ))}
    </div>
  );
}
