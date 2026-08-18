import { CheckCircle2 } from "lucide-react";
import { actionCardText, type ChatAction } from "@/lib/chat";

interface ChatActionCardProps {
  action: ChatAction;
}

/**
 * One bordered, green-striped confirmation for an executed trade or
 * watchlist change (D-04). `actionCardText` is the only source of the
 * rendered sentence and the only gate on whether anything renders at all —
 * this component has no other render path, so a card is never shown for an
 * action that did not happen (T-04-22). Hand-built `<div>`, not a shadcn
 * card, per `04-UI-SPEC.md`'s Design System note.
 */
export function ChatActionCard({ action }: ChatActionCardProps) {
  const text = actionCardText(action);
  if (text === null) return null;

  return (
    <div className="rounded-md border border-border bg-card px-3 py-2 text-body border-l-2 border-l-up">
      <div className="flex items-center gap-1">
        <CheckCircle2 size={14} className="text-up" />
        <span className="numeric">{text}</span>
      </div>
    </div>
  );
}
