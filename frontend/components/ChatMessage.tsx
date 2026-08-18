import type { ReactNode } from "react";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  /** Plan 04's action cards slot in here without restructuring this file. */
  children?: ReactNode;
}

/**
 * One transcript bubble. Both roles share the same shell — `max-w-[80%]`
 * plus `whitespace-pre-wrap break-words` so the model's line breaks survive
 * and an unbroken string (e.g. a URL) wraps instead of blowing out the
 * 256px box. The assistant bubble carries the two-pixel Accent Yellow left
 * stripe (D-01); the user bubble carries none — alignment plus the stripe
 * are the only markers distinguishing them. `content` always renders as a
 * React text node, never through a raw-HTML injection prop, since the
 * string originates from a model whose output is untrusted (T-04-09).
 */
export function ChatMessage({ role, content, children }: ChatMessageProps) {
  const isAssistant = role === "assistant";

  return (
    <div
      className={`max-w-[80%] rounded-md bg-muted px-3 py-2 text-body whitespace-pre-wrap break-words ${
        isAssistant ? "self-start border-l-2 border-l-[#ecad0a]" : "self-end"
      }`}
    >
      {content}
      {children && <div className="mt-2">{children}</div>}
    </div>
  );
}
