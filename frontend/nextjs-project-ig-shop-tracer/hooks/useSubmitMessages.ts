"use client";

/**
 * useSubmitMessages
 *
 * Maintains a short-lived queue of toast-style messages. Each message becomes
 * invisible after 5 s (for a CSS fade-out) and is removed from the queue
 * 300 ms later. Timers are cleaned up on unmount so no callback runs against
 * a stale component.
 *
 * Collaborators:
 *   - `components/storebook/SubmitMessageStack.tsx` renders the returned
 *     `messages` array.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export type SubmitMessage = {
  id: number;
  isVisible: boolean;
  text: string;
};

export type UseSubmitMessagesResult = {
  messages: SubmitMessage[];
  /** Enqueue a message; it will fade out automatically. */
  showMessage: (text: string) => void;
};

// How long the message stays fully visible before the fade-out begins.
const MESSAGE_VISIBLE_MS = 5000;
// Delay between fade-out start and removal from the DOM. Matches the CSS
// transition duration so the element finishes animating before being unmounted.
const MESSAGE_CLEANUP_DELAY_MS = 300;

export function useSubmitMessages(): UseSubmitMessagesResult {
  const [messages, setMessages] = useState<SubmitMessage[]>([]);
  const timeoutsRef = useRef<Array<ReturnType<typeof setTimeout>>>([]);
  const nextIdRef = useRef(0);

  const showMessage = useCallback((text: string) => {
    const nextId = nextIdRef.current + 1;
    nextIdRef.current = nextId;

    setMessages((prev) => [...prev, { id: nextId, isVisible: true, text }]);

    const hideTimer = setTimeout(() => {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === nextId ? { ...message, isVisible: false } : message,
        ),
      );
    }, MESSAGE_VISIBLE_MS);
    timeoutsRef.current.push(hideTimer);

    const cleanupTimer = setTimeout(() => {
      setMessages((prev) => prev.filter((message) => message.id !== nextId));
    }, MESSAGE_VISIBLE_MS + MESSAGE_CLEANUP_DELAY_MS);
    timeoutsRef.current.push(cleanupTimer);
  }, []);

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach((timerId) => clearTimeout(timerId));
      timeoutsRef.current = [];
    };
  }, []);

  return { messages, showMessage };
}
