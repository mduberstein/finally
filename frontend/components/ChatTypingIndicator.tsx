/**
 * Three CSS-animated dots inside an assistant-shaped bubble — occupies the
 * position of the next assistant reply (D-03) while a `POST /api/chat`
 * request is in flight. Same bubble shell and Accent Yellow left stripe as
 * `ChatMessage`'s assistant variant, since it carries the same "this came
 * from the AI assistant" identity. Under `prefers-reduced-motion: reduce`
 * the dots stay visible at a fixed opacity (see `globals.css`) rather than
 * disappearing — this is the sole loading signal, so suppressing the motion
 * must not suppress the signal.
 */
export function ChatTypingIndicator() {
  return (
    <div className="max-w-[80%] self-start rounded-md border-l-2 border-l-[#ecad0a] bg-muted px-3 py-2">
      <div className="flex items-center gap-1">
        <span
          className="size-1.5 animate-typing-dot rounded-full bg-muted-foreground"
          style={{ animationDelay: "0ms" }}
        />
        <span
          className="size-1.5 animate-typing-dot rounded-full bg-muted-foreground"
          style={{ animationDelay: "150ms" }}
        />
        <span
          className="size-1.5 animate-typing-dot rounded-full bg-muted-foreground"
          style={{ animationDelay: "300ms" }}
        />
      </div>
    </div>
  );
}
